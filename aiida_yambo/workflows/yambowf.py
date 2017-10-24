import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.common.exceptions import InputValidationError,ValidationError
from aiida.orm.data.upf import get_pseudos_from_structure
from aiida.common.datastructures import calc_states
from collections import defaultdict
from aiida.orm.utils import DataFactory, CalculationFactory
import itertools
from aiida.orm.data.base import Float, Str, NumericType, BaseType, Bool
from aiida.work.workchain import WorkChain, while_
from aiida.work.workchain import ToContext as ResultToContext
from aiida.work.run import legacy_workflow
from aiida.work.run import run, submit
from aiida.common.links import LinkType
from aiida_yambo.workflows.yambo_utils import default_step_size, update_parameter_field, set_default_qp_param,\
               default_pw_settings, set_default_pw_param, yambo_default_settings, default_qpkrange, p2y_default_settings
from aiida.orm.data.remote import RemoteData 
from aiida.orm.data.array.kpoints import KpointsData
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida_yambo.workflows.yamborestart  import YamboRestartWf
from aiida_yambo.workflows.pwplaceholder  import PwRestartWf
from aiida_yambo.calculations.gw  import YamboCalculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.workflows.pw.base  import PwBaseWorkChain

#PwCalculation = CalculationFactory('quantumespresso.pw')
#YamboCalculation = CalculationFactory('yambo.yambo')
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
            cls.report_wf
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
            parent_calc = self.inputs.parent_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
            if isinstance(parent_calc, YamboCalculation):
                self.ctx.last_step_kind = 'yambo' 
                self.ctx.yambo_res = DataFactory('parameter')(dict={"yambo_pk": parent_calc.pk } )
            elif isinstance(parent_calc, PwCalculation):
                self.ctx.last_step_kind = 'pw'
                self.ctx.pw_wf_res = None  
            else:
                self.ctx.pw_wf_res = None  
        
    def can_continue(self):
        if self.ctx.last_step_kind == 'yambo' and self.ctx.yambo_res: 
            self.ctx.yambo_pks.append(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]) 
            if self.ctx.yambo_res.out.gw.get_dict()["success"] == True:
                self.ctx.done = True

        if self.ctx.last_step_kind == 'yambo_p2y' and self.ctx.yambo_res : 
            self.ctx.yambo_pks.append(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]) 

        if self.ctx.last_step_kind == 'pw' and self.ctx.pw_wf_res != None : 
            self.ctx.pw_pks.append(self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"]) 

        if self.ctx.done == True:
            return False
        self.ctx.can_cont +=1
        if self.ctx.can_cont> 10 :
            return False 
        return True
 
    def perform_next(self):
        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y' :
            if load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]).get_state() == u'FINISHED':
                if self.inputs.to_set_qpkrange  and 'QPkrange' not in self.inputs.parameters_yambo.get_dict().keys():
                    self.inputs.parameters_yambo = default_qpkrange( self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"], self.inputs.parameters_yambo)
                is_initialize = load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]).inp.settings.get_dict().pop('INITIALISE', None)
                if is_initialize: # YamboRestartWf will initialize before starting QP calc  for us, 
                    yambo_result =  self.run_yambo()
                    return  ResultToContext( yambo_res= yambo_result  )
                else:  # Possibly a restart,  after some type of failure, why was is not handled by YamboRestartWf? 
                    self.report(" possible bug in restart code {} ".format(self.ctx.last_step_kind)  )
            if len(self.ctx.yambo_pks) > 0:
                 if load_node(self.ctx.yambo_pks[-1] ).get_state() == u'FAILED':  # Needs a resubmit depending on the error.
                    self.report(" last calculation failed:  type: {} pk:  ".format(self.ctx.last_step_kind, self.ctx.yambo_pks[-1] ))

        if  self.ctx.last_step_kind == 'pw' and  self.ctx.pw_wf_res :
            if self.ctx.pw_wf_res.out.pw.get_dict()['success'] == True:
                self.report(" PwRestartWf was successful, nscf pk={} running initialize next with: YamboRestartWf ".format(parentcalc.pk))
                p2y_result = self.run_initialize()
                return  ResultToContext( yambo_res= p2y_result )
            if self.ctx.pw_wf_res.out.pw.get_dict()['success'] == False:
                self.report("PwRestartWf subworkflow  NOT  successful")
                return 

        if  self.ctx.last_step_kind == None or self.ctx.last_step_kind == 'pw' and not self.ctx.pw_wf_res :# this is likely  the very begining, we can start with the scf/nscf here
            extra = {}
            self.report("will run PwRestartWf subworkflow next  ")
            if 'parameters_pw_nscf' in self.inputs.keys():
                extra['parameters_nscf'] = self.inputs.parameters_pw_nscf.copy() 
            if 'parent_folder' in self.inputs.keys():
                extra['parent_folder'] = self.inputs.parent_folder
            pw_wf_result = self.run_pw()
            return  ResultToContext( pw_wf_res = pw_wf_result  )

    def run_yambo(self):
        parentcalc = load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"])
        parent_folder = parentcalc.out.remote_folder 
        yambo_result = submit (YamboRestartWf,precode= self.inputs.codename_p2y.copy(), yambocode=self.inputs.codename_yambo.copy(),
             parameters = self.inputs.parameters_yambo.copy(), calculation_set= self.inputs.calculation_set_yambo.copy(),
            parent_folder = parent_folder, settings = self.inputs.settings_yambo.copy() )
        self.ctx.last_step_kind = 'yambo'
        self.report ("submitted YamboRestartWf subworkflow, in Initialize mode  ")
        return yambo_result

    def run_initialize(self):
        parentcalc = load_node(self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"])
        parent_folder = parentcalc.out.remote_folder 
        p2y_result = submit (YamboRestartWf, precode= self.inputs.codename_p2y.copy(), yambocode=self.inputs.codename_yambo.copy(),
             parameters = self.inputs.parameters_p2y.copy() , calculation_set= self.inputs.calculation_set_p2y.copy(),
            parent_folder = parent_folder, settings = self.inputs.settings_p2y.copy() )
        self.ctx.last_step_kind = 'yambo_p2y'
        return p2y_result

    def run_pw(self):
        pw_wf_result = submit(PwRestartWf, codename = self.inputs.codename_pw.copy()  , pseudo_family = self.inputs.pseudo_family.copy(), 
                calculation_set = self.inputs.calculation_set_pw.copy(), settings=self.inputs.settings_pw.copy(), 
                kpoints=self.inputs.kpoint_pw.copy(), gamma= self.inputs.gamma_pw.copy(),
                structure = self.inputs.structure.copy() , parameters = self.inputs.parameters_pw.copy(), **extra)
        self.ctx.last_step_kind = 'pw'                   
        return pw_wf_result  
        

    def report_wf(self):
        """
        """
        from aiida.orm import DataFactory
        pw = self.ctx.pw_wf_res.out.pw.get_dict()
        gw = self.ctx.yambo_res.out.gw.get_dict()
        gw.update(pw)
        self.report ("wf done  {} {}  ".format(pw , gw))
        self.out("gw", DataFactory('parameter')(dict=gw ))

if __name__ == "__main__":
    pass
