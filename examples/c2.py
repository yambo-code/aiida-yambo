from __future__ import print_function
StructureData = DataFactory('structure')
cell = [[15.8753100000, 0.0000000000, 0.0000000000],
        [0.0000000000, 15.8753100000, 0.0000000000],
        [0.0000000000, 0.0000000000, 2.4696584760]]
s = StructureData(cell=cell)
s.append_atom(
    position=(0.0000000000, 0.0000000000, -0.5857830640), symbols='C')
s.append_atom(position=(0.6483409550, 0.0000000000, 0.5857863990), symbols='C')
s.append_atom(
    position=(-1.0769905460, 0.0000000000, -0.5902956470), symbols='H')
s.append_atom(position=(1.7253315010, 0.0000000000, 0.5902989820), symbols='H')
print(s.store())
