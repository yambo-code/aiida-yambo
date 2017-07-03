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

try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType, Bool
    from aiida.work.workchain import WorkChain, while_
    from aiida.work.workchain import ToContext as ResultToContext
    from aiida.work.run import legacy_workflow
    from aiida.work.run import run, submit
except ImportError:
    from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData 
    from aiida.workflows2.db_types import  SimpleData  as BaseType
    from aiida.orm.data.simple import  SimpleData as SimpleData_
    from aiida.workflows2.run import run 
    from aiida.workflows2.fragmented_wf import FragmentedWorkfunction as WorkChain
    from aiida.workflows2.fragmented_wf import ( ResultToContext, while_)

from aiida.workflows.user.epfl_theos.quantumespresso.pw import PwWorkflow
from aiida.orm.data.remote import RemoteData 
from aiida.orm.data.array.kpoints import KpointsData
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.orm.calculation.job.yambo  import YamboCalculation
from aiida.workflows.user.cnr_nano.yamborestart  import YamboRestartWf
from aiida.workflows.user.cnr_nano.pwplaceholder  import PwRestartWf
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation 

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
YamboProcess = YamboCalculation.process()

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
        spec.input("input_pw", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoint_pw", valid_type=KpointsData)
        spec.input("gamma_pw", valid_type=Bool, default=Bool(0) )
        spec.input("parameters_pw", valid_type=ParameterData)
        spec.input("parameters_pw_nscf", valid_type=ParameterData,default=ParameterData(dict={}))
        spec.input("parameters_p2y", valid_type=ParameterData)
        spec.input("parameters_yambo", valid_type=ParameterData)
        spec.input("parent_folder", valid_type=RemoteData,required=False)
        spec.outline(
            cls.start_workflow,
            while_(cls.can_continue)(
                cls.perform_next,
            ),
            cls.report
        )
        spec.dynamic_output()

    def start_workflow(self):
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
        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y' :
            if load_node(self.ctx.yambo_res.get_dict()["yambo_pk"]).get_state() == 'FINISHED':
                is_initialize = load_node(self.ctx.yambo_res.get_dict()["yambo_pk"]).inp.settings.get_dict().pop('INITIALISE', None)
                if is_initialize: # after init we run yambo 
                    parentcalc = load_node(self.ctx.yambo_res.get_dict()["yambo_pk"])
                    parent_folder = parentcalc.out.remote_folder 
                    p2y_result = run (YamboRestartWf,precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
                         parameters = self.inputs.parameters_yambo, calculation_set= self.inputs.calculation_set_yambo,
                        parent_folder = parent_folder, settings = self.inputs.settings_yambo )
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
                parentcalc = load_node(self.ctx.pw_wf_res.get_dict()["nscf_pk"])
                parent_folder = parentcalc.out.remote_folder 
                p2y_result = run (YamboRestartWf, precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
                     parameters = self.inputs.parameters_p2y, calculation_set= self.inputs.calculation_set_p2y,
                    parent_folder = parent_folder, settings = self.inputs.settings_p2y )
                self.ctx.last_step_kind = 'yambo_p2y'
                self.ctx.yambo_res = p2y_result["gw"]
                self.ctx.yambo_pks.append(p2y_result["gw"].get_dict()["yambo_pk"]) 
                return  #ResultToContext( yambo_res= p2y_result )
            if self.ctx.pw_wf_res.get_dict()['success'] == False:
                # PwRestartWf could not run 
                return 

        if  self.ctx.last_step_kind == None or self.ctx.last_step_kind == 'pw' and not self.ctx.pw_wf_res :# this is likely  the very begining, we can start with the scf/nscf here
            parent_folder = None
            if 'parent_folder' in self.inputs.keys():
                pw_wf_result = run(PwRestartWf, codename = self.inputs.codename_pw, pseudo_family = self.inputs.pseudo_family, 
                        calculation_set = self.inputs.calculation_set_pw, settings=self.inputs.settings_pw, 
                        inpt=self.inputs.input_pw, kpoints=self.inputs.kpoint_pw, gamma= self.inputs.gamma_pw,
                        structure = self.inputs.structure, parameters = self.inputs.parameters_pw,parameters_nscf=self.inputs.parameters_pw_nscf,
                        parent_folder=self.inputs.parent_folder)
            else:
                pw_wf_result = run(PwRestartWf, codename = self.inputs.codename_pw, pseudo_family = self.inputs.pseudo_family, 
                        calculation_set = self.inputs.calculation_set_pw, settings=self.inputs.settings_pw, 
                        inpt=self.inputs.input_pw, kpoints=self.inputs.kpoint_pw, gamma= self.inputs.gamma_pw,
                        structure = self.inputs.structure, parameters = self.inputs.parameters_pw,parameters_nscf=self.inputs.parameters_pw_nscf,
                        )
            print("pw_wf_result", pw_wf_result)
            self.ctx.pw_wf_res = pw_wf_result["pw"]
            self.ctx.pw_pks.append(pw_wf_result["pw"].get_dict()["nscf_pk"]) 
            self.ctx.last_step_kind = 'pw'                    
            return  #ResultToContext( pw_wf_res = pw_wf_result  )




    def perform_next_legacy(self):
        # THIS DOES NOT WORK, WILL WORK IN 0.8.8 with `legacy_workflow` adapter.
        # PwCalc, with scf in calculation_type, next is nscf,
        #              nscf in calculation_type, next is yambo p2y
        # Yambocalc,  if initialise true next is yambo run
        # yambocalc,  if initialize false, next  report.
        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y' :
            if load_node(self.ctx.last_step_pk).get_state() == 'FINISHED':
                is_initialize = load_node(self.ctx.last_step_pk).inp.settings.get_dict().pop('INITIALISE', None)
                if is_initialize: # run non yambo run
                    pass
                    self.ctx.last_step_kind = 'yambo'
                else:
                    pass  #  run  with initialize
                    self.ctx.last_step_kind = 'yambo_p2y'
            if load_node(self.ctx.last_step_pk).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass

        if  self.ctx.last_step_kind == 'pw':
            #a = load_workflow(self.ctx.scf_wf_pk) ;  a.get_all_calcs()[-1]
            if load_node(self.ctx.last_step_pk).get_state() == 'FINISHED':
                if load_node(self.ctx.last_step_pk).inp.parameters.get_dict()['CONTROL']['calculation'] == 'scf': # we now do an nscf calc
                    pass
                elif load_node(self.ctx.last_step_pk).inp.parameters.get_dict()['CONTROL']['calculation'] == 'nscf' : # we can move to yambo init
                    pass 
            if load_node(self.ctx.last_step_pk).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass
               
        if  self.ctx.last_step_kind == None :  # this is likely  the very begining, we can start with the scf here
            wf = PwWorkflow(params = self.inputs.pwwf_parameters)
            wf.start()
            self.ctx.scf_wf_pk =  wf.pk 
            self.ctx.last_step_kind = 'pw'
            
       

    def report(self):
        """
        """
        from aiida.orm import DataFactory
        self.out("gw", DataFactory('parameter')(dict={ "pw": self.ctx.pw_wf_res.get_dict(), "gw":self.ctx.yambo_res.get_dict() }))

if __name__ == "__main__":
    pass
