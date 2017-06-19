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
    from aiida.workflows2.run import run 
    from aiida.workflows2.fragmented_wf import FragmentedWorkfunction as WorkChain
    from aiida.workflows2.fragmented_wf import ( ResultToContext, while_)

from aiida.orm.data.remote import RemoteData 
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation
#import sys,os
#sys.path.append(os.path.realpath(__file__))
from aiida.workflows.user.cnr_nano.yambo_utils import generate_pw_input_params 

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
PwProcess = PwCalculation.process()


class PwRestartWf(WorkChain):
    """
    """

    @classmethod
    def _define(cls, spec):
        """
        Workfunction definition
        """
        spec.input("codename", valid_type=BaseType)
        spec.input("pseudo_family", valid_type=SimpleData)
        spec.input("calculation_set", valid_type=ParameterData) # custom_scheduler_commands,  resources,...
        spec.input("settings", valid_type=ParameterData)
        spec.input("inpt", valid_type=ParameterData)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoints", valid_type=KpointsData)
        spec.input("gamma", valid_type=SimpleData, default=False)
        spec.input("parameters", valid_type=ParameterData)
        spec.input("parameters_nscf", valid_type=ParameterData, default=False)
        spec.input("parent_folder", valid_type=RemoteData,default=False)
        spec.outline(
            cls.pwbegin,
            while_(cls.pw_should_continue)(
                cls.pw_continue,
            ),
            cls.report
        )
        spec.dynamic_output()

    def pwbegin(self, ctx):
        """
        start SCF/NSCF 
        """
        if self.inputs.parent_folder != None:
            if not isinstance(self.inputs.parent_folder, RemoteData):
                raise InputValidationError("parent_calc_folder must be of"
                                       " type RemoteData")
 
        parameters = self.inputs.parameters
        inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                     self.inputs.parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma,self.inputs.settings, self.inputs.parent_folder)
        future = self.submit(PwProcess, inputs)
        ctx.pw_pks = []
        ctx.pw_pks.append(future.pid)
        ctx.restart = 0 
        ctx.success = False
        return ResultToContext(pw=future)

    def pw_should_continue(self, ctx):
        if ctx.success == True:
            return False
        if ctx.restart > 5:
            return False
        if len (ctx.pw_pks) < 1: 
            return True 
        calc = load_node(ctx.pw_pks[-1])
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'scf' and  calc.get_state()== 'FINISHED':
            ctx.scf_pk = ctx.pw_pks[-1] 
            return True 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  ctx.restart < 4:
            return True
        if calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED':
            ctx.nscf_pk = ctx.pw_pks[-1] 
            ctx.success = True
            return False 
        if calc.get_state() == calc_states.SUBMISSIONFAILED or calc.get_state() == calc_states.FAILED\
            or 'output_parameters' not in calc.get_outputs_dict()  and  ctx.restart >= 4:
            ctx.success = False
            return False
        return False

    def pw_continue(self, ctx):
        # restart if neccessary
        calc = load_node(ctx.pw_pks[-1])
        parameters = calc.get_inputs_dict()['parameters'].get_dict()
        scf = ''
        parent_folder = None
        if parameters['CONTROL']['calculation'] == 'scf' and calc.get_state()== 'FINISHED':
            scf = 'nscf'
            parent_folder = calc.out.remote_folder
            ctx.scf_pk = ctx.pw_pks[-1] 
        if parameters['CONTROL']['calculation'] == 'nscf' and  calc.get_state()== 'FINISHED': 
            ctx.nscf_pk = ctx.pw_pks[-1] 
            ctx.success = True
            ctx.restart += 1 # so we do not end up in an infinite loop 
            return # we are finished, ideally we should not need to arrive here, this is also done at self.pw_should_continue
 
        if scf == 'nscf':
            if 'force_symmorphic' not in parameters['SYSTEM']:
                 parameters['SYSTEM']['force_symmorphic'] = True 
            if 'nbnd' not in parameters['SYSTEM']:
                 parameters['SYSTEM']['nbnd'] = calc.get_outputs_dict()['output_parameters'].get_dict()['number_of_electrons']*2
            
        parameters['CONTROL']['calculation'] = scf  
        parameters = ParameterData(dict=parameters)  
        if self.inputs.parameters_nscf:
            parameters = self.inputs.parameters_nscf
        inputs = generate_pw_input_params(self.inputs.structure, self.inputs.codename, self.inputs.pseudo_family,
                      parameters, self.inputs.calculation_set, self.inputs.kpoints,self.inputs.gamma, self.inputs.settings, parent_folder )
        future = self.submit(PwProcess, inputs)
        ctx.pw_pks.append(future.pid)
        ctx.restart += 1

    def report(self,ctx):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        from aiida.orm import DataFactory
        self.out("pw", DataFactory('parameter')(dict= {"scf_pk": ctx.scf_pk , "nscf_pk": ctx.nscf_pk, 'success': ctx.success }) ) 

if __name__ == "__main__":
    pass
