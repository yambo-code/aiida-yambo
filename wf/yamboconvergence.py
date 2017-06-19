import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from collections import defaultdict
from aiida.orm.utils import DataFactory
from aiida.orm.data.base import Float, Str, NumericType, BaseType
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.work.run import run, submit
from aiida.work.workchain import WorkChain, while_, ToContext
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation
from aiida.orm.calculation.job.yambo  import YamboCalculation

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
PwProcess = PwCalculation.process()
YamboProcess = YamboCalculation.process()

"""
   
"""

class YamboConvergenceWorkflow(WorkChain):
    """
    Converge to minimum using Newton's algorithm on the first derivative of the energy (minus the pressure).
    """

    @classmethod
    def _define(cls, spec):
        """
        """
        spec.outline(
        )
        spec.dynamic_output()

    def report(self, ctx):
        """
        Output final quantities
        """
        from aiida.orm import DataFactory
        self.out("steps", DataFactory('parameter')(dict={
            }))

if __name__ == "__main__":
    pass
