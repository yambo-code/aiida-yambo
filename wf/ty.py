import numpy as np
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

calc = load_node(4586)
table=calc.out.array_qp.get_array('qp_table') # ik, ib, ispn
lowest_k = calc.inp.parameters.get_dict()['QPkrange'][0][0] # first kpoint listed, 
lowest_b = calc.inp.parameters.get_dict()['QPkrange'][0][-2] # first band on first kpoint listed,
highest_b = calc.inp.parameters.get_dict()['QPkrange'][0][-1]  # last band on first kpoint listed,
print(calc.inp.parameters.get_dict()['QPkrange'][0], " calc.inp.parameters.get_dict()['QPkrange'][0]")
print(lowest_k, lowest_b,  highest_b, "lowest_k, lowest_b,  highest_b")
argwlk = np.argwhere(table[:,0]==float(lowest_k))  # indexes for lowest kpoint
argwlb = np.argwhere(table[:,1]==float(lowest_b))  # indexes for lowest band
argwhb = np.argwhere(table[:,1]==float(highest_b)) # indexes for highest band
if  len(argwlk)< 1:
    argwlk = np.array([0]) 
if len(argwhb) < 1:
    argwhb = np.argwhere(table[:,1]== table[:,1][np.argmax(table[:,1])])
    argwlb = np.argwhere(table[:,1]== table[:,1][np.argmax(table[:,1])]-1 )
print(argwlk, argwlb, argwhb  , " argwlk, argwlb, argwhb")
arglb = np.intersect1d(argwlk,argwlb)              # index for lowest kpoints' lowest band
arghb = np.intersect1d(argwlk,argwhb)              # index for lowest kpoint's highest band
e_m_eo = calc.out.array_qp.get_array('E_minus_Eo')
eo = calc.out.array_qp.get_array('Eo')
corrected = eo+e_m_eo
print(arglb, arghb , " arglb, arghb")
corrected_lb = corrected[arglb]
corrected_hb = corrected[arghb]
print(corrected_hb,corrected_hb, corrected_hb- corrected_lb, " :corrected_hb,corrected_hb, corrected_hb- corrected_lb ")
print (corrected_hb- corrected_lb) 
