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
        Necessary information:  codename_pw , pseudo_family, calculation_set_pw , calculation_set_p2y,
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
        spec.input("previous_yambo_workchain", valid_type=Str,required=False)
        spec.input("to_set_qpkrange", valid_type=Bool,required=False, default=Bool(0) )
        spec.input("bands_groupname", valid_type=Str, required=False)
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
                self.ctx.yambo_res = DataFactory('parameter')(dict={"out":{"yambo_pk": parent_calc.pk }} )
                self.report("Yambo calculation (pk {}) found in input, I will start from there.".format(parent_calc.pk ))
            elif isinstance(parent_calc, PwCalculation):
                self.ctx.last_step_kind = 'pw'
                self.ctx.pw_wf_res = None
                self.report("PW calculation (pk {}) found in input, I will start from there.".format(parent_calc.pk ))
            else:
                self.ctx.pw_wf_res = None
                self.report("No PW or Yambo calculation found in input, I will start from scratch.")
        if 'previous_yambo_workchain' in self.inputs.keys():
            self.report('WARNING: previous_yambo_workchain option should be used in DEBUG mode only!')
            self.ctx.last_step_kind = 'yambo'
            self.ctx.yambo_res = load_node(int(str(self.inputs.previous_yambo_workchain)))
            self.report("DEBUG: workchain {} loaded".format(self.ctx.yambo_res))

        try:
            self.ctx.bands_groupname = self.inputs.bands_groupname
            self.report("GW bands will be added to the group {}".format(self.inputs.bands_groupname))
        except AttributeError:
            self.ctx.bands_groupname = None
        self.ctx.parameters_yambo = self.inputs.parameters_yambo 

        self.report(" workflow initilization step completed.")
        
    def can_continue(self):
        if self.ctx.last_step_kind == 'yambo' and self.ctx.yambo_res:
            try:
                self.ctx.yambo_pks.append(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"])
            except AttributeError:
                raise InputValidationError("Yambo input must be a workchain!")
            if self.ctx.yambo_res.out.gw.get_dict()["success"] == True:
                self.ctx.done = True
                self.report("Last Yambo calculation was succesful.")

        if self.ctx.last_step_kind == 'yambo_p2y' and self.ctx.yambo_res : 
            self.ctx.yambo_pks.append(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]) 

        if self.ctx.last_step_kind == 'pw' and self.ctx.pw_wf_res != None : 
            self.ctx.pw_pks.append(self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"]) 

        if self.ctx.done == True:
            self.report("Workflow has finished. will report outputs")
            return False
        self.ctx.can_cont +=1
        if self.ctx.can_cont> 10 :
            return False 
        return True
 
    def perform_next(self):
        if self.ctx.last_step_kind == 'yambo' or self.ctx.last_step_kind == 'yambo_p2y' :
            if load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]).get_state() == u'FINISHED':
                if self.inputs.to_set_qpkrange   and 'QPkrange' not in self.ctx.parameters_yambo.get_dict().keys():
                    self.ctx.parameters_yambo = default_qpkrange( self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"], self.ctx.parameters_yambo)
                start_from_initialize = load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"]).inp.settings.get_dict().pop('INITIALISE', None)

                if start_from_initialize: # YamboRestartWf will initialize before starting QP calc  for us, 
                    self.report ("YamboRestartWf will start from initialise mode (yambo init) ")
                    yambo_result =  self.run_yambo()
                    return  ResultToContext( yambo_res= yambo_result  )
                else:  # Possibly a restart,  after some type of failure, why was is not handled by YamboRestartWf? 
                    self.report(" possible bug in restart code {} ".format(self.ctx.last_step_kind)  )
            if len(self.ctx.yambo_pks) > 0:
                 if load_node(self.ctx.yambo_pks[-1] ).get_state() == u'FAILED':  # Needs a resubmit depending on the error.
                    self.report("Last {} calculation (pk: {}) failed, will attempt a restart".format(self.ctx.last_step_kind, self.ctx.yambo_pks[-1] ))

        if  self.ctx.last_step_kind == 'pw' and  self.ctx.pw_wf_res :
            if self.ctx.pw_wf_res.out.pw.get_dict()['success'] == True:
                self.report("PwRestartWf was successful,  running initialize next with: YamboRestartWf ")
                p2y_result = self.run_initialize()
                return  ResultToContext( yambo_res= p2y_result )
            if self.ctx.pw_wf_res.out.pw.get_dict()['success'] == False:
                self.report("PwRestartWf subworkflow  NOT  successful")
                return 

        if  self.ctx.last_step_kind == None or self.ctx.last_step_kind == 'pw' and not self.ctx.pw_wf_res :# this is likely  the very begining, we can start with the scf/nscf here
            extra = {}
            self.report("Launching PwRestartWf ")
            if 'parameters_pw_nscf' in self.inputs.keys():
                extra['parameters_nscf'] = self.inputs.parameters_pw_nscf 
            if 'parent_folder' in self.inputs.keys():
                extra['parent_folder'] = self.inputs.parent_folder
            pw_wf_result = self.run_pw(extra)
            return  ResultToContext( pw_wf_res = pw_wf_result  )

    def run_yambo(self):
        parentcalc = load_node(self.ctx.yambo_res.out.gw.get_dict()["yambo_pk"])
        parent_folder = parentcalc.out.remote_folder 
        yambo_result = submit (YamboRestartWf,precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
             parameters = self.ctx.parameters_yambo, calculation_set= self.inputs.calculation_set_yambo,
            parent_folder = parent_folder, settings = self.inputs.settings_yambo )
        self.ctx.last_step_kind = 'yambo'
        self.report ("submitted YamboRestartWf subworkflow, in Initialize mode  ")
        return yambo_result

    def run_initialize(self):
        parentcalc = load_node(self.ctx.pw_wf_res.out.pw.get_dict()["nscf_pk"])
        parent_folder = parentcalc.out.remote_folder 
        p2y_result = submit (YamboRestartWf, precode= self.inputs.codename_p2y, yambocode=self.inputs.codename_yambo,
             parameters = self.inputs.parameters_p2y , calculation_set= self.inputs.calculation_set_p2y,
            parent_folder = parent_folder, settings = self.inputs.settings_p2y )
        self.ctx.last_step_kind = 'yambo_p2y'
        return p2y_result

    def run_pw(self, extra):
        pw_wf_result = submit(PwRestartWf, codename = self.inputs.codename_pw  , pseudo_family = self.inputs.pseudo_family, 
                calculation_set = self.inputs.calculation_set_pw, settings=self.inputs.settings_pw, 
                kpoints=self.inputs.kpoint_pw, gamma= self.inputs.gamma_pw,
                structure = self.inputs.structure , parameters = self.inputs.parameters_pw, **extra)
        self.ctx.last_step_kind = 'pw'                   
        return pw_wf_result  
        

    def report_wf(self):
        """
        """
        self.report('Final step.')
        from aiida.orm import DataFactory
        pw = self.ctx.pw_wf_res.out.pw.get_dict()
        gw = self.ctx.yambo_res.out.gw.get_dict()
        gw.update(pw)
        self.out("yambo_remote_folder", self.ctx.yambo_res.out.yambo_remote_folder)
        self.out("scf_remote_folder", self.ctx.pw_wf_res.out.scf_remote_folder)
        self.out("nscf_remote_folder", self.ctx.pw_wf_res.out.nscf_remote_folder)
        if self.ctx.bands_groupname is not None:
            g_bands,_ = Group.get_or_create(name=self.ctx.bands_groupname)
            g_bands.add_nodes(self.ctx.yambo_res)
            self.report("Yambo calc (pk: {}) added to the group {}".format(yambo_res.pk, self.ctx.bands_groupname))
        else:
            self.report ("Yambo calc done (pk: {}  ".format(gw))
        self.out("gw", DataFactory('parameter')(dict=gw ))
        self.report("workflow complete")

if __name__ == "__main__":
    pass
