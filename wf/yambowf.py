import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.common.exceptions import InputValidationError,ValidationError
from aiida.orm.data.upf import get_pseudos_from_structure
from aiida.common.datastructures import calc_states
from collections import defaultdict
from aiida.orm.utils import DataFactory
import itertools
from aiida.orm.data.base import Float, Str, NumericType, BaseType, Bool
from aiida.work.workchain import WorkChain, while_
from aiida.work.workchain import ToContext as ResultToContext
from aiida.work.run import legacy_workflow
from aiida.work.run import run, submit

from aiida.workflows.user.cnr_nano.yambo_utils import default_step_size, update_parameter_field, set_default_qp_param,\
               default_pw_settings, set_default_pw_param, yambo_default_settings, default_qpkrange, p2y_default_settings
from aiida.orm.data.remote import RemoteData 
from aiida.orm.data.array.kpoints import KpointsData
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.workflows.user.cnr_nano.yamborestart  import YamboRestartWf
from aiida.workflows.user.cnr_nano.pwplaceholder  import PwRestartWf
from aiida.orm.calculation.job.yambo  import YamboCalculation
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation 

ParameterData = DataFactory("parameter")

class YamboWorkflow(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        """
        Workfunction definition
        Neccessary information:  codename_pw , pseudo_family, calculation_set_pw , calculation_set_p2y, 
                                 calculation_set_yambo, structure, kpoints, parameters_pw, parameters_gw, settings_pw,
                                 codename_p2y, codename_yambo ,  input_pw
        """
        super(YamboWorkflow, cls).define(spec)
        spec.input("codename_pw", valid_type=Str)
        spec.input("codename_p2y", valid_type=Str)
        spec.input("codename_yambo", valid_type=Str)
        spec.input("pseudo_family", valid_type=Str)
        spec.input("calculation_set_pw", valid_type=ParameterData) # custom_scheduler_commands,  resources,...
        spec.input("calculation_set_p2y", valid_type=ParameterData)
        spec.input("calculation_set_yambo", valid_type=ParameterData)
        spec.input("settings_pw", valid_type=ParameterData)
        spec.input("settings_p2y", valid_type=ParameterData)
        spec.input("settings_yambo", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoint_pw", valid_type=KpointsData)
        spec.input("gamma_pw", valid_type=Bool, default=Bool(0), required=False )
        spec.input("parameters_pw", valid_type=ParameterData)
        spec.input("parameters_pw_nscf", valid_type=ParameterData,required=False)
        spec.input("parameters_p2y", valid_type=ParameterData)
        spec.input("parameters_yambo", valid_type=ParameterData)
        spec.input("parent_folder", valid_type=RemoteData,required=False)
        spec.input("to_set_qpkrange", valid_type=Bool,required=False, default=Bool(0) )
        spec.outline(
            cls.start_workflow,
            while_(cls.can_continue)(
                cls.perform_next,
            ),
            cls.report
        )
        spec.dynamic_output()

    def start_workflow(self):
        self.ctx.pw_wf_res = DataFactory('parameter')(dict={})
        self.ctx.yambo_res = DataFactory('parameter')(dict={})
        self.ctx.last_step_pw_wf = None
        self.ctx.last_step_kind = None
        self.ctx.can_cont  = 0
        self.ctx.yambo_pks = [] 
        self.ctx.pw_pks  = [] 
        self.ctx.done = False
        if 'parent_folder' in self.inputs.keys():
            parent_calc = self.inputs.parent_folder.get_inputs_dict()['remote_folder']
            if isinstance(parent_calc, YamboCalculation):
                self.ctx.last_step_kind = 'yambo' 
            if isinstance(parent_calc, PwCalculation):
                self.ctx.last_step_kind = 'pw'
                self.ctx.pw_wf_res = None  
        
    def can_continue(self):
        if self.ctx.done == True:
            return False
        self.ctx.can_cont +=1
        if self.ctx.can_cont> 10 :
            return False 
        return True
 
    def perform_next(self):
        print (" at perform next in yambowf", self.ctx.last_step_kind, self.ctx.pw_wf_res)
        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y' :
            print (" last step kind ",  self.ctx.last_step_kind, load_node(self.ctx.yambo_res.get_dict()["yambo_pk"]).get_state() )
            if load_node(self.ctx.yambo_res.get_dict()["yambo_pk"]).get_state() == 'FINISHED':
                print(" at qp")
                if self.inputs.to_set_qpkrange  and 'QPkrange' not in self.inputs.parameters_yambo.get_dict().keys():
                    self.inputs.parameters_yambo = default_qpkrange( self.ctx.pw_wf_res.get_dict()["nscf_pk"], self.inputs.parameters_yambo)
                is_initialize = load_node(self.ctx.yambo_res.get_dict()["yambo_pk"]).inp.settings.get_dict().pop('INITIALISE', None)
                print(" at qp")
                if is_initialize: # after init we run yambo 
                    parentcalc = load_node(self.ctx.yambo_res.get_dict()["yambo_pk"])
                    parent_folder = parentcalc.out.remote_folder 
                    p2y_result = run (YamboRestartWf,precode= self.inputs.codename_p2y.copy(), yambocode=self.inputs.codename_yambo.copy(),
                         parameters = self.inputs.parameters_yambo.copy(), calculation_set= self.inputs.calculation_set_yambo.copy(),
                        parent_folder = parent_folder, settings = self.inputs.settings_yambo.copy() )
                    self.ctx.last_step_kind = 'yambo'
                    self.ctx.yambo_res = p2y_result["gw"]
                    self.ctx.yambo_pks.append(p2y_result["gw"].get_dict()["yambo_pk"]) 
                    if p2y_result["gw"].get_dict()["success"] == True:
                        self.ctx.done = True
                    return  #ResultToContext( yambo_res= p2y_result["pw"])
                else:  # Possibly a restart, 
                    pass 
            if load_node(self.ctx.yambo_pks[-1]).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass

        if  self.ctx.last_step_kind == 'pw' and  self.ctx.pw_wf_res :
            if self.ctx.pw_wf_res.get_dict()['success'] == True:
                print(" at p2y")
                parentcalc = load_node(self.ctx.pw_wf_res.get_dict()["nscf_pk"])
                parent_folder = parentcalc.out.remote_folder 
                p2y_result = run (YamboRestartWf, precode= self.inputs.codename_p2y.copy(), yambocode=self.inputs.codename_yambo.copy(),
                     parameters = self.inputs.parameters_p2y.copy() , calculation_set= self.inputs.calculation_set_p2y.copy(),
                    parent_folder = parent_folder, settings = self.inputs.settings_p2y.copy() )
                self.ctx.last_step_kind = 'yambo_p2y'
                self.ctx.yambo_res = p2y_result["gw"]
                self.ctx.yambo_pks.append(p2y_result["gw"].get_dict()["yambo_pk"]) 
                return  #ResultToContext( yambo_res= p2y_result )
            if self.ctx.pw_wf_res.get_dict()['success'] == False:
                # PwRestartWf could not run 
                return 

        if  self.ctx.last_step_kind == None or self.ctx.last_step_kind == 'pw' and not self.ctx.pw_wf_res :# this is likely  the very begining, we can start with the scf/nscf here
            extra = {}
            if 'parameters_pw_nscf' in self.inputs.keys():
                extra['parameters_nscf'] = self.inputs.parameters_pw_nscf.copy() 
            if 'parent_folder' in self.inputs.keys():
                extra['parent_folder'] = self.inputs.parent_folder
            pw_wf_result = run(PwRestartWf, codename = self.inputs.codename_pw.copy()  , pseudo_family = self.inputs.pseudo_family.copy(), 
                    calculation_set = self.inputs.calculation_set_pw.copy(), settings=self.inputs.settings_pw.copy(), 
                    kpoints=self.inputs.kpoint_pw.copy(), gamma= self.inputs.gamma_pw.copy(),
                    structure = self.inputs.structure.copy() , parameters = self.inputs.parameters_pw.copy(), **extra)
            self.ctx.pw_wf_res = pw_wf_result["pw"]
            self.ctx.pw_pks.append(pw_wf_result["pw"].get_dict()["nscf_pk"]) 
            self.ctx.last_step_kind = 'pw'                    
            return  #ResultToContext( pw_wf_res = pw_wf_result  )




    def report(self):
        """
        """
        print ("wf done")
        from aiida.orm import DataFactory
        pw = self.ctx.pw_wf_res.get_dict()
        gw = self.ctx.yambo_res.get_dict()
        gw.update(pw)
        print(gw, "gd")
        self.out("gw", DataFactory('parameter')(dict=gw ))
if __name__ == "__main__":
    pass
