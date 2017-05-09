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
from aiida.orm.calculation.job.yambo  import YamboCalculation
#import sys,os
#sys.path.append(os.path.realpath(__file__))
#from  aiida.parsers.yambo_utils import  generate_yambo_input_params
from aiida.workflows.user.cnr_nano.yambo_utils import generate_yambo_input_params 

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
YamboProcess = YamboCalculation.process()

"""
"""
class YamboRestartWf(WorkChain):
    """
    """

    @classmethod
    def _define(cls, spec):
        """
        Workfunction definition
        """
        spec.input("precode", valid_type=BaseType)
        spec.input("yambocode", valid_type=BaseType)
        spec.input("calculation_set", valid_type=ParameterData)
        spec.input("settings", valid_type=ParameterData)
        spec.input("parent_folder", valid_type=RemoteData)
        spec.input("parameters", valid_type=ParameterData)
        spec.outline(
            cls.yambobegin,
            while_(cls.yambo_should_restart)(
                cls.yambo_restart,
            ),
            cls.report
        )
        spec.dynamic_output()

    def yambobegin(self, ctx):
        """
        Run the  pw-> yambo conversion, init and yambo run
        #  precodename,yambocodename, parent_folder, parameters,  calculation_set=None, settings
        """
        # run YamboCalculation
        if not isinstance(self.inputs.parent_folder, RemoteData):
            raise InputValidationError("parent_calc_folder must be of"
                                       " type RemoteData")        
        parameters = self.inputs.parameters
        inputs = generate_yambo_input_params(
             self.inputs.precode,self.inputs.yambocode,
            self.inputs.parent_folder, parameters, self.inputs.calculation_set, self.inputs.settings )
        future = self.submit(YamboProcess, inputs)
        ctx.yambo_pks = []
        ctx.yambo_pks.append(future.pid)
        ctx.restart = 0 
        return ResultToContext(yambo=future)

    def yambo_should_restart(self, ctx):
        # This needs to restart calculations, within limits, 
        # should restart a calculation if it satisfies either
        # 1. It hasnt been restarted  2 times already.
        # 2. It hasnt produced output.
        # 3. Submission failed.
        # 
        if ctx.restart > 5:
            return False
        calc = load_node(ctx.yambo_pks[-1])
        if calc.get_state() == calc_states.SUBMISSIONFAILED\
                   or calc.get_state() == calc_states.FAILED\
                   or 'output_parameters' not in calc.get_outputs_dict():
            return True
            
        return False

    def yambo_restart(self, ctx):
        # restart if neccessary
        # get inputs from prior calculation ctx.yambo_pks
        calc = load_node(ctx.yambo_pks[-1])
        parameters = calc.get_inputs_dict()['parameters'].get_dict()
        parent_folder = calc.out.remote_folder
        inputs = generate_yambo_input_params(
             self.inputs.precode,self.inputs.yambocode,
             parent_folder, ParameterData(dict=parameters), self.inputs.calculation_set, self.inputs.settings )
        future = self.submit(YamboProcess, inputs)
        ctx.yambo_pks.append(future.pid)
        ctx.restart += 1

    def report(self,ctx):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        from aiida.orm import DataFactory
        success = load_node(ctx.yambo_pks[-1]).get_state()== 'FINISHED' 
        self.out("gw", DataFactory('parameter')(dict={ "yambo_pk":   ctx.yambo_pks[-1], "success": success }))

if __name__ == "__main__":
    pass
