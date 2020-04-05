from __future__ import absolute_import
from __future__ import print_function
import numpy as np
import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
from aiida.orm import load_node
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_yambo.calculations.gw import YamboCalculation

node_id = 52908
calc = load_node(node_id)
table = calc.out.array_qp.get_array('qp_table')
parent_calc = calc.inp.parent_calc_folder.inp.remote_folder
e_m_eo = calc.out.array_qp.get_array('E_minus_Eo')
eo = calc.out.array_qp.get_array('Eo')
corrected = eo + e_m_eo
spinp = None
nelec = None
if isinstance(parent_calc, YamboCalculation):
    has_found_nelec = False
    while (not has_found_nelec):
        try:
            nelec = parent_calc.out.output_parameters.get_dict(
            )['number_of_electrons']
            nbands = parent_calc.out.output_parameters.get_dict(
            )['number_of_bands']
            has_found_nelec = True
            if parent_calc.out.output_parameters.get_dict()['lsda']== True or\
                parent_calc.out.output_parameters.get_dict()['non_colinear_calculation'] == True :
                spinp = True
            else:
                spinp = False
        except AttributeError:
            parent_calc = parent_calc.inp.parent_calc_folder.inp.remote_folder
        except KeyError:
            parent_calc = parent_calc.inp.parent_calc_folder.inp.remote_folder
elif isinstance(parent_calc, PwCalculation):
    nelec = parent_calc.out.output_parameters.get_dict()['number_of_electrons']
    nbands = parent_calc.out.output_parameters.get_dict()['number_of_bands']
    if parent_calc.out.output_parameters.get_dict()['lsda']== True or\
            parent_calc.out.output_parameters.get_dict()['non_colinear_calculation'] == True:
        spinp = True
    else:
        spinp = False
# Filter rows with bands  nocc and nocc+1
vbm = int(nelec / 2)
cbm = vbm + 1

if spinp:
    table = table[table[:, -1] == 1]  # we look at the majority spin only

vbm_cbm = table[(table[:, 1] >= vbm) & (table[:, 1] <= cbm)]
# find the max vbm from all vbm rows,  same for cbm, subtract, and get their associated kpt, band info
vbm_only = vbm_cbm[vbm_cbm[:, 1] == vbm]
cbm_only = vbm_cbm[vbm_cbm[:, 1] == cbm]
vbm_arg_max = np.argmax(vbm_only[:, -1])
cbm_arg_max = np.argmin(cbm_only[:, -1])
vbm_arg = np.argwhere(table[:, -1] == vbm_only[:, -1][vbm_arg_max])[0][0]
cbm_arg = np.argwhere(table[:, -1] == cbm_only[:, -1][cbm_arg_max])[0][0]
kpt_vbm = table[:, 0][vbm_arg]
band_vbm = table[:, 1][vbm_arg]
kpt_cbm = table[:, 0][cbm_arg]
band_cbm = table[:, 1][cbm_arg]
gap = table[:, -1][cbm_arg] - table[:, -1][vbm_arg]
print("vbm  kpt ", kpt_vbm, " band: ", band_vbm)
print("cbm  kpt ", kpt_cbm, " band: ", band_cbm)
print("gap ", gap)
