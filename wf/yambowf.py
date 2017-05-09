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
    from aiida.orm.data.base import Float, Str, NumericType, BaseType 
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

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
YamboProcess = YamboCalculation.process()

class YamboWorkflow(WorkChain):
    """
    Converge to minimum using Newton's algorithm on the first derivative of the energy (minus the pressure).
    """

    @classmethod
    def _define(cls, spec):
        """
        Workfunction definition
        Neccessary information:  codename_pw , pseudo_family, calculation_set_pw , calculation_set_p2y, 
                                 calculation_set_yambo, structure, kpoints, parameters_pw, parameters_gw, settings_pw,
                                 codename_p2y, codename_yambo ,  input_pw
        """
        spec.input("codename_pw", valid_type=BaseType)
        spec.input("codename_p2y", valid_type=BaseType)
        spec.input("codename_yambo", valid_type=BaseType)
        spec.input("pseudo_family", valid_type=BaseType)
        spec.input("calculation_set_pw", valid_type=ParameterData) # custom_scheduler_commands,  resources,...
        spec.input("calculation_set_p2y", valid_type=ParameterData)
        spec.input("calculation_set_yambo", valid_type=ParameterData)
        spec.input("settings_pw", valid_type=ParameterData)
        spec.input("settings_p2y", valid_type=ParameterData)
        spec.input("settings_yambo", valid_type=ParameterData)
        spec.input("input_pw", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoint_pw", valid_type=KpointsData)
        spec.input("gamma_pw", valid_type=SimpleData_, default=False)
        spec.input("parameters_pw", valid_type=ParameterData)
        spec.input("parameters_pw_nscf", valid_type=ParameterData,default=False)
        spec.input("parameters_p2y", valid_type=ParameterData)
        spec.input("parameters_yambo", valid_type=ParameterData)
        spec.outline(
            cls.start_workflow,
            while_(cls.can_continue)(
                cls.perform_next,
            ),
            cls.report
        )
        spec.dynamic_output()

    def start_workflow(self, ctx):
        ctx.last_step_pw_wf = None
        ctx.last_step_kind = None
        ctx.can_cont  = 0
        ctx.yambo_pks = [] 
        ctx.pw_pks  = [] 
        ctx.done = False
    def can_continue(self, ctx):
        if ctx.done == True:
            return False
        ctx.can_cont +=1
        if ctx.can_cont> 10 :
            return False 
        return True
 
    def perform_next(self, ctx):
        if ctx.last_step_kind == 'yambo' or ctx.last_step_kind == 'yambo_p2y' :
            if load_node(ctx.yambo_res.get_dict()["yambo_pk"]).get_state() == 'FINISHED':
                is_initialize = load_node(ctx.yambo_res.get_dict()["yambo_pk"]).inp.settings.get_dict().pop('INITIALISE', None)
                if is_initialize: # after init we run yambo 
                    parentcalc = load_node(ctx.yambo_res.get_dict()["yambo_pk"])
                    parent_folder = parentcalc.out.remote_folder 
                    p2y_result =run(YamboRestartWf,precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
                         parameters = self.inputs.parameters_yambo, calculation_set= self.inputs.calculation_set_yambo,
                        parent_folder = parent_folder, settings = self.inputs.settings_yambo )
                    ctx.last_step_kind = 'yambo'
                    ctx.yambo_res = p2y_result["gw"]
                    ctx.yambo_pks.append(p2y_result["gw"].get_dict()["yambo_pk"]) 
                    if p2y_result["gw"].get_dict()["success"] == True:
                        ctx.done = True
                else:  # Possibly a restart, 
                    pass 
            if load_node(ctx.yambo_pks[-1]).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass

        if  ctx.last_step_kind == 'pw':
            if ctx.pw_wf_res.get_dict()['success'] == True:
                parentcalc = load_node(ctx.pw_wf_res.get_dict()["nscf_pk"])
                parent_folder = parentcalc.out.remote_folder 
                p2y_result =run (YamboRestartWf, precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
                     parameters = self.inputs.parameters_p2y, calculation_set= self.inputs.calculation_set_p2y,
                    parent_folder = parent_folder, settings = self.inputs.settings_p2y )
                ctx.last_step_kind = 'yambo_p2y'
                ctx.yambo_res = p2y_result["gw"]
                ctx.yambo_pks.append(p2y_result["gw"].get_dict()["yambo_pk"]) 

            if ctx.pw_wf_res.get_dict()['success'] == False:
                # PwRestartWf could not run 
                return 

        if  ctx.last_step_kind == None :  # this is likely  the very begining, we can start with the scf here
            pw_wf_result = run(PwRestartWf, codename = self.inputs.codename_pw, pseudo_family = self.inputs.pseudo_family, 
                        calculation_set = self.inputs.calculation_set_pw, settings=self.inputs.settings_pw, 
                        inpt=self.inputs.input_pw, kpoints=self.inputs.kpoint_pw, gamma= self.inputs.gamma_pw,
                        structure = self.inputs.structure, parameters = self.inputs.parameters_pw,parameters_nscf=self.inputs.parameters_pw_nscf)
            ctx.pw_wf_res = pw_wf_result["pw"]
            ctx.pw_pks.append(pw_wf_result["pw"].get_dict()["nscf_pk"]) 
            ctx.last_step_kind = 'pw'                    




    def perform_next_legacy(self, ctx):
        # THIS DOES NOT WORK, WILL WORK IN 0.8.8 with `legacy_workflow` adapter.
        # PwCalc, with scf in calculation_type, next is nscf,
        #              nscf in calculation_type, next is yambo p2y
        # Yambocalc,  if initialise true next is yambo run
        # yambocalc,  if initialize false, next  report.
        if ctx.last_step_kind == 'yambo' or ctx.last_step_kind == 'yambo_p2y' :
            if load_node(ctx.last_step_pk).get_state() == 'FINISHED':
                is_initialize = load_node(ctx.last_step_pk).inp.settings.get_dict().pop('INITIALISE', None)
                if is_initialize: # run non yambo run
                    pass
                    ctx.last_step_kind = 'yambo'
                else:
                    pass  #  run  with initialize
                    ctx.last_step_kind = 'yambo_p2y'
            if load_node(ctx.last_step_pk).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass

        if  ctx.last_step_kind == 'pw':
            #a = load_workflow(ctx.scf_wf_pk) ;  a.get_all_calcs()[-1]
            if load_node(ctx.last_step_pk).get_state() == 'FINISHED':
                if load_node(ctx.last_step_pk).inp.parameters.get_dict()['CONTROL']['calculation'] == 'scf': # we now do an nscf calc
                    pass
                elif load_node(ctx.last_step_pk).inp.parameters.get_dict()['CONTROL']['calculation'] == 'nscf' : # we can move to yambo init
                    pass 
            if load_node(ctx.last_step_pk).get_state() == 'FAILED':  # Needs a resubmit depending on the error.
                pass
               
        if  ctx.last_step_kind == None :  # this is likely  the very begining, we can start with the scf here
            wf = PwWorkflow(params = self.inputs.pwwf_parameters)
            wf.start()
            ctx.scf_wf_pk =  wf.pk 
            ctx.last_step_kind = 'pw'
            
       

    def report(self,ctx):
        """
        """
        from aiida.orm import DataFactory
        self.out("gw", DataFactory('parameter')(dict={ "pw": ctx.pw_wf_res.get_dict(), "gw":ctx.yambo_res.get_dict() }))

if __name__ == "__main__":
    pass
