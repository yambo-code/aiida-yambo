from __future__ import absolute_import
from __future__ import print_function
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')

from ase.spacegroup import crystal
a = 5.388
cell = crystal(
    'Si', [(0, 0, 0)],
    spacegroup=227,
    cellpar=[a, a, a, 90, 90, 90],
    primitive_cell=True)
struc = StructureData(ase=cell)  #

print((struc.store()))
