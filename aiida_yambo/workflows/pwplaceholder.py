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

from aiida.orm.data.remote import RemoteData 
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.workflows.user.cnr_nano.yambo_utils import generate_pw_input_params 
from aiida_quantumespresso.calculations.pw import PwCalculation

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
#PwCalculation = CalculationFactory('quantumespresso.pw')
PwProcess = PwCalculation.process()
YamboCalculation = CalculationFactory('yambo.yambo')

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
            cls.report
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
            calc = parent_folder.get_inputs_dict()['remote_folder']
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
                if  'parameters_nscf' in  self.inputs.keys() :
                    parameters = self.inputs.parameters_nscf
                inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)
                self.ctx.scf_pk = calc.pk 

            if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state() != 'FINISHED':#  starting from failed SCF
                inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        self.inputs.parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)
                
            if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED':# next nscf
                self.ctx.nscf_pk = calc.pk # NSCF is done, we should exit  
        else:
           inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                        self.inputs.parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, parent_folder)

        future = submit(PwProcess, **inputs)
        self.ctx.pw_pks = []
        self.ctx.pw_pks.append(future.pid)
        self.ctx.restart = 0 
        self.ctx.success = False
        self.ctx.scf_pk = None 
        self.ctx.nscf_pk = None
        return ResultToContext(first_pk=Outputs(future)  )

    def pw_should_continue(self):
        if len(self.ctx.pw_pks) ==0: # we never run a single calculation 
            return False 

        if self.ctx.success == True:
            return False
        if self.ctx.restart > 5:
            return False
        if len (self.ctx.pw_pks) < 1: 
            return True 
        calc = load_node(self.ctx.pw_pks[-1])
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state()== 'FINISHED':
            self.ctx.scf_pk = self.ctx.pw_pks[-1] 
            return True 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  self.ctx.restart < 4:
            return True
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED':
            self.ctx.nscf_pk = self.ctx.pw_pks[-1] 
            self.ctx.success = True
            return False 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  self.ctx.restart >= 4:
            self.ctx.success = False
            return False
        return False

    def pw_continue(self):
        # restart if neccessary
        calc = load_node(self.ctx.pw_pks[-1])
        parameters = calc.get_inputs_dict()['parameters'].get_dict()
        scf = ''
        parent_folder = None
        if parameters['CONTROL']['calculation'] == 'scf' and calc.get_state()== 'FINISHED':
            scf = 'nscf'
            parent_folder = calc.out.remote_folder
            self.ctx.scf_pk = self.ctx.pw_pks[-1] 
        if parameters['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED': 
            self.ctx.nscf_pk = self.ctx.pw_pks[-1] 
            self.ctx.success = True
            self.ctx.restart += 1 # so we do not end up in an infinite loop 
            return # we are finished, ideally we should not need to arrive here, this is also done at self.pw_should_continue
 
        if scf == 'nscf':
            if 'force_symmorphic' not in parameters['SYSTEM']:
                 parameters['SYSTEM']['force_symmorphic'] = True 
            if 'nbnd' not in parameters['SYSTEM']:
                 try:
                     parameters['SYSTEM']['nbnd'] = calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_electrons']*2
                 except KeyError:
                     parameters['SYSTEM']['nbnd'] = int(calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_bands']*1.2) # 20% more
            
        parameters['CONTROL']['calculation'] = scf  
        parameters = ParameterData(dict=parameters)  
        if 'parameters_nscf' in self.inputs.keys():
            parameters = self.inputs.parameters_nscf
        inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                      parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma, self.inputs.settings, parent_folder )
        future =  submit (PwProcess, **inputs)
        self.ctx.pw_pks.append(future.pid)
        self.ctx.restart += 1
        return  ResultToContext(last_pk=Outputs(future))

    def report(self):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        from aiida.orm import DataFactory
        self.out("pw", DataFactory('parameter')(dict= {"scf_pk": self.ctx.scf_pk , "nscf_pk": self.ctx.nscf_pk, 'success': self.ctx.success }) ) 

if __name__ == "__main__":
    pass
