from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')




cell = [[5.3976054000,    0.0000000000,    0.0000000000 ],
        [0.0000000000,    5.3976054000,    0.0000000000 ],
        [0.0000000000,    0.0000000000,    5.3976054000 ],
       ]
struc = StructureData(cell=cell)
struc.append_atom(position=( 2.6988027000,     2.6988027000,     0.0000000000), symbols='Si')
struc.append_atom(position=( 0.0000000000,     0.0000000000,     0.0000000000), symbols='Si')
struc.append_atom(position=( 2.6988027000,     0.0000000000,     2.6988027000), symbols='Si')
struc.append_atom(position=( 0.0000000000,     2.6988027000,     2.6988027000), symbols='Si')
struc.append_atom(position=( 4.0482040500,     4.0482040500,     1.3494013500), symbols='Si')
struc.append_atom(position=( 1.3494013500,     1.3494013500,     1.3494013500), symbols='Si')
struc.append_atom(position=( 4.0482040500,     1.3494013500,     4.0482040500), symbols='Si')
struc.append_atom(position=( 1.3494013500,     4.0482040500,     4.0482040500), symbols='Si')

print (struc.store()) 
