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

try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType ,Bool
    from aiida.work.workchain import WorkChain, while_, Outputs
    from aiida.work.workchain import ToContext as ResultToContext
    from aiida.work.run import legacy_workflow
    from aiida.work.run import run, submit
except ImportError:
     pass
from aiida.common.links import LinkType
from aiida.orm.data.remote import RemoteData 
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida_yambo.workflows.yambo_utils import generate_pw_input_params 
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_yambo.calculations.gw  import YamboCalculation

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
#PwCalculation = CalculationFactory('quantumespresso.pw')
PwProcess = PwCalculation.process()
#YamboCalculation = CalculationFactory('yambo.yambo')

class PwRestartWf(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        """
        Workfunction definition
        """
        super(PwRestartWf, cls).define(spec)
        spec.input("codename", valid_type=BaseType)
        spec.input("pseudo_family", valid_type=Str)
        spec.input("calculation_set", valid_type=ParameterData) # custom_scheduler_commands,  resources,...
        spec.input("settings", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoints", valid_type=KpointsData)
        spec.input("gamma", valid_type=Bool, default=Bool(0), required=False)
        spec.input("parameters", valid_type=ParameterData)
        spec.input("parameters_nscf", valid_type=ParameterData ,required=False)
        spec.input("parent_folder", valid_type=RemoteData,required=False)
        spec.outline(
            cls.pwbegin,
            while_(cls.pw_should_continue)(
                cls.pw_continue,
            ),
            cls.report_wf
        )
        spec.dynamic_output()

    def pwbegin(self):
        """
        start SCF/NSCF 
        """
        if 'parent_folder' in  self.inputs.keys() :
            if not isinstance(self.inputs.parent_folder, RemoteData):
                raise InputValidationError("parent_calc_folder when defined must be of"
                                       " type RemoteData")
        parent_folder = None
        inputs={}
        if 'parent_folder' in self.inputs.keys():
            parameters = self.inputs.parameters.get_dict()
            parent_folder=self.inputs.parent_folder
            calc = parent_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
            if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state()== 'FINISHED':# next nscf 
                if 'force_symmorphic' not in parameters['SYSTEM']:
                     parameters['SYSTEM']['force_symmorphic'] = True
                if 'nbnd' not in parameters['SYSTEM']:
                     try:
                         parameters['SYSTEM']['nbnd'] = calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_electrons']*2
                     except KeyError:
                         parameters['SYSTEM']['nbnd'] = int(calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_bands']*1.2) # 20% more
                parameters['CONTROL']['calculation'] = 'nscf'
                parameters = ParameterData(dict=parameters)
                if  'parameters_nscf' in  self.inputs.keys():
                    parameters = self.inputs.parameters_nscf
                inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)
                self.ctx.scf_pk = calc.pk
                self.report(" submitted NSCF {} ".format(calc.pk)) 

            if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state() != 'FINISHED':#  starting from failed SCF
                self.report("restarting failed   SCF  {} ".format(calc.pk))
                inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        self.inputs.parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)
                
            if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED':# 
                self.report(" workflow completed nscf successfully, exiting")
                self.ctx.nscf_pk = calc.pk # NSCF is done, we should exit  
        else:
           self.report("Running from SCF")
           inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        self.inputs.parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)

        future = submit( PwBaseWorkChain, **inputs)
        self.ctx.pw_pks = []
        self.ctx.pw_pks.append(future.pid)
        self.ctx.restart = 0 
        self.ctx.success = False
        self.ctx.scf_pk = None 
        self.ctx.nscf_pk = None
        self.report("submitted subworkflow  {}".format(future.pid))
        return ResultToContext(first_calc=future  )

    def pw_should_continue(self):
        """
        """
        if len(self.ctx.pw_pks) ==0: # we never run a single calculation 
            return False 

        if self.ctx.success == True:
            return False
        if self.ctx.restart > 4:
            return False
        if len (self.ctx.pw_pks) < 1: 
            return True 
        calc = None
        if len(self.ctx.pw_pks) ==1:
            calc = load_node(self.ctx.first_calc.out.CALL.pk)
        else:
            calc = load_node(self.ctx.last_calc.out.CALL.pk)
        self.report("calc {} ".format(calc))
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state()== 'FINISHED':
            self.ctx.scf_pk = calc.pk 
            self.report(" completed SCF successfully")
            return True 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  self.ctx.restart < 4:
            self.report(" calculation failed  {}, will try restarting".format(calc.pk))
            return True
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED':
            self.ctx.nscf_pk =  calc.pk 
            self.ctx.success = True
            self.report("completed NSCF successfully, exiting")
            return False 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  self.ctx.restart >= 4:
            self.ctx.success = False
            self.report("workflow failed to succesfully run any calcultions exiting")
            return False
        self.report("worklfow exiting unsuccessfully ")
        return False

    def pw_continue(self):
        # restart if neccessary
        calc = None
        if len(self.ctx.pw_pks) ==1:
            calc = load_node(self.ctx.first_calc.out.CALL.pk)
        else:
            calc = load_node(self.ctx.last_calc.out.CALL.pk)
        self.report(" continuing from calculation {}".format(calc.pk))
        parameters = calc.get_inputs_dict()['parameters'].get_dict()
        scf = ''
        parent_folder = None
        if parameters['CONTROL']['calculation'] == 'scf' and calc.get_state()== 'FINISHED':
            scf = 'nscf'
            parent_folder = calc.out.remote_folder
            self.ctx.scf_pk = calc.pk
        elif parameters['CONTROL']['calculation'] == 'scf' and calc.get_state()!= 'FINISHED':
            scf = 'scf'  # RESTART
            parent_folder = calc.out.remote_folder
            self.ctx.restart += 1 # so we do not end up in an infinite loop 
        elif parameters['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED': 
            self.ctx.nscf_pk = calc.pk
            self.ctx.success = True
            self.ctx.restart += 1 # so we do not end up in an infinite loop 
            return # we are finished, ideally we should not need to arrive here, this is also done at self.pw_should_continue
        elif parameters['CONTROL']['calculation'] == 'nscf' and calc.get_state()!= 'FINISHED':
            scf = 'nscf'  # RESTART
            parent_folder = calc.out.remote_folder
            self.ctx.restart += 1 # so we do not end up in an infinite loop 
        else:
            self.ctx.success = False
            self.report("workflow in an inconsistent state.")
            return 
 
        if scf == 'nscf':
            if 'force_symmorphic' not in parameters['SYSTEM']:
                 parameters['SYSTEM']['force_symmorphic'] = True 
            if 'nbnd' not in parameters['SYSTEM']:
                 try:
                     parameters['SYSTEM']['nbnd'] = calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_electrons']*2
                 except KeyError:
                     parameters['SYSTEM']['nbnd'] = int(calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_bands']*1.2) # 20% more
        parameters['CONTROL']['calculation'] = scf  
        self.report(" calculation type:  {} and system {}".format(parameters['CONTROL']['calculation'], parameters['SYSTEM'])) 
        parameters = ParameterData(dict=parameters)  
        if 'parameters_nscf' in self.inputs.keys():
            parameters = self.inputs.parameters_nscf
        inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                      parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma, self.inputs.settings, parent_folder )
        #future =  submit (PwProcess, **inputs)
        future =  submit (PwBaseWorkChain, **inputs)
        self.ctx.pw_pks.append(future.pid)
        self.ctx.restart += 1
        self.report("submitted pw  subworkflow  {}".format(future.pid))
        return  ResultToContext(last_calc=future)



    def report_wf(self):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        self.report("Workflow Complete : scf {}  nscf {} success {}".format(self.ctx.scf_pk,self.ctx.nscf_pk,self.ctx.success))
        from aiida.orm import DataFactory
        res = {}
        if self.ctx.scf_pk:
            res['scf_pk'] = self.ctx.scf_pk
        if self.ctx.nscf_pk:
            res['nscf_pk'] = self.ctx.nscf_pk
        res['success'] = self.ctx.success 
        self.out("pw", DataFactory('parameter')(dict=res )) 
        self.out("scf_remote_folder", load_node(self.ctx.scf_pk).out.remote_folder ) 
        self.out("nscf_remote_folder",  load_node(self.ctx.nscf_pk).out.remote_folder ) 


if __name__ == "__main__":
    pass
