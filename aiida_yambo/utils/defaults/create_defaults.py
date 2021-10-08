# -*- coding: utf-8 -*-
"""default input creation"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import json

try:
    from aiida.orm import Dict, Str, load_node, KpointsData, RemoteData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
except:
    pass

scf = {"SYSTEM": {"nbnd": int(20), "ecutwfc": 60.0, "force_symmorphic": True}, "CONTROL": {"verbosity": "high", "wf_collect": True, "calculation": "scf"}, "ELECTRONS": {"conv_thr": 1e-08, "mixing_beta": 0.7, "mixing_mode": "plain", "diago_full_acc": True, "diago_thr_init": 5e-06}}
nscf = {"SYSTEM": {"nbnd": int(500), "ecutwfc": 60.0, "force_symmorphic": True}, "CONTROL": {"verbosity": "high", "wf_collect": True, "calculation": "nscf"}, "ELECTRONS": {"conv_thr": 1e-08, "mixing_beta": 0.6, "mixing_mode": "plain", "diago_full_acc": True, "diago_thr_init": 5e-06, "diagonalization": "david"}}
periodic_table = {"H": {"valence": 1.0, "Ecut_Ry": {"normal": 72.0, "high": 84.0}}, "He": {"valence": 2.0, "Ecut_Ry": {"normal": 90.0, "high": 98.0}}, "Li": {"valence": 3.0, "Ecut_Ry": {"normal": 74.0, "high": 82.0}}, "Be": {"valence": 4.0, "Ecut_Ry": {"normal": 88.0, "high": 100.0}}, "B": {"valence": 3.0, "Ecut_Ry": {"normal": 76.0, "high": 88.0}}, "C": {"valence": 4.0, "Ecut_Ry": {"normal": 82.0, "high": 90.0}}, "N": {"valence": 5.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "O": {"valence": 6.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "F": {"valence": 7.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Ne": {"valence": 8.0, "Ecut_Ry": {"normal": 68.0, "high": 80.0}}, "Na": {"valence": 9.0, "Ecut_Ry": {"normal": 88.0, "high": 96.0}}, "Mg": {"valence": 10.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Al": {"valence": 11.0, "Ecut_Ry": {"normal": 40.0, "high": 52.0}}, "Si": {"valence": 4.0, "Ecut_Ry": {"normal": 36.0, "high": 48.0}}, "P": {"valence": 5.0, "Ecut_Ry": {"normal": 44.0, "high": 56.0}}, "S": {"valence": 6.0, "Ecut_Ry": {"normal": 52.0, "high": 64.0}}, "Cl": {"valence": 7.0, "Ecut_Ry": {"normal": 58.0, "high": 66.0}}, "Ar": {"valence": 8.0, "Ecut_Ry": {"normal": 66.0, "high": 74.0}}, "K": {"valence": 9.0, "Ecut_Ry": {"normal": 74.0, "high": 86.0}}, "Ca": {"valence": 10.0, "Ecut_Ry": {"normal": 68.0, "high": 76.0}}, "Sc": {"valence": 11.0, "Ecut_Ry": {"normal": 78.0, "high": 90.0}}, "Ti": {"valence": 12.0, "Ecut_Ry": {"normal": 84.0, "high": 92.0}}, "V": {"valence": 13.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Cr": {"valence": 14.0, "Ecut_Ry": {"normal": 94.0, "high": 110.0}}, "Mn": {"valence": 15.0, "Ecut_Ry": {"normal": 96.0, "high": 108.0}}, "Fe": {"valence": 16.0, "Ecut_Ry": {"normal": 90.0, "high": 106.0}}, "Co": {"valence": 17.0, "Ecut_Ry": {"normal": 96.0, "high": 108.0}}, "Ni": {"valence": 18.0, "Ecut_Ry": {"normal": 98.0, "high": 110.0}}, "Cu": {"valence": 19.0, "Ecut_Ry": {"normal": 92.0, "high": 104.0}}, "Zn": {"valence": 20.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Ga": {"valence": 13.0, "Ecut_Ry": {"normal": 80.0, "high": 92.0}}, "Ge": {"valence": 14.0, "Ecut_Ry": {"normal": 78.0, "high": 90.0}}, "As": {"valence": 5.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Se": {"valence": 6.0, "Ecut_Ry": {"normal": 86.0, "high": 98.0}}, "Br": {"valence": 7.0, "Ecut_Ry": {"normal": 46.0, "high": 58.0}}, "Kr": {"valence": 8.0, "Ecut_Ry": {"normal": 52.0, "high": 68.0}}, "Rb": {"valence": 9.0, "Ecut_Ry": {"normal": 46.0, "high": 58.0}}, "Sr": {"valence": 10.0, "Ecut_Ry": {"normal": 68.0, "high": 80.0}}, "Y": {"valence": 11.0, "Ecut_Ry": {"normal": 72.0, "high": 84.0}}, "Zr": {"valence": 12.0, "Ecut_Ry": {"normal": 66.0, "high": 98.0}}, "Nb": {"valence": 13.0, "Ecut_Ry": {"normal": 82.0, "high": 98.0}}, "Mo": {"valence": 14.0, "Ecut_Ry": {"normal": 80.0, "high": 92.0}}, "Tc": {"valence": 15.0, "Ecut_Ry": {"normal": 84.0, "high": 96.0}}, "Ru": {"valence": 16.0, "Ecut_Ry": {"normal": 84.0, "high": 100.0}}, "Rh": {"valence": 17.0, "Ecut_Ry": {"normal": 88.0, "high": 100.0}}, "Pd": {"valence": 18.0, "Ecut_Ry": {"normal": 82.0, "high": 98.0}}, "Ag": {"valence": 19.0, "Ecut_Ry": {"normal": 82.0, "high": 94.0}}, "Cd": {"valence": 20.0, "Ecut_Ry": {"normal": 102.0, "high": 114.0}}, "In": {"valence": 13.0, "Ecut_Ry": {"normal": 70.0, "high": 82.0}}, "Sn": {"valence": 14.0, "Ecut_Ry": {"normal": 72.0, "high": 84.0}}, "Sb": {"valence": 15.0, "Ecut_Ry": {"normal": 80.0, "high": 88.0}}, "Te": {"valence": 16.0, "Ecut_Ry": {"normal": 80.0, "high": 92.0}}, "I": {"valence": 17.0, "Ecut_Ry": {"normal": 70.0, "high": 82.0}}, "Xe": {"valence": 18.0, "Ecut_Ry": {"normal": 68.0, "high": 84.0}}, "Cs": {"valence": 9.0, "Ecut_Ry": {"normal": 50.0, "high": 58.0}}, "Ba": {"valence": 10.0, "Ecut_Ry": {"normal": 44.0, "high": 56.0}}, "La": {"valence": 11.0, "Ecut_Ry": {"normal": 110.0, "high": 130.0}}, "Lu": {"valence": 25.0, "Ecut_Ry": {"normal": 100.0, "high": 116.0}}, "Hf": {"valence": 26.0, "Ecut_Ry": {"normal": 58.0, "high": 70.0}}, "Ta": {"valence": 27.0, "Ecut_Ry": {"normal": 58.0, "high": 70.0}}, "W": {"valence": 28.0, "Ecut_Ry": {"normal": 74.0, "high": 82.0}}, "Re": {"valence": 15.0, "Ecut_Ry": {"normal": 72.0, "high": 84.0}}, "Os": {"valence": 16.0, "Ecut_Ry": {"normal": 74.0, "high": 86.0}}, "Ir": {"valence": 17.0, "Ecut_Ry": {"normal": 68.0, "high": 80.0}}, "Pt": {"valence": 18.0, "Ecut_Ry": {"normal": 84.0, "high": 100.0}}, "Au": {"valence": 19.0, "Ecut_Ry": {"normal": 76.0, "high": 88.0}}, "Hg": {"valence": 20.0, "Ecut_Ry": {"normal": 66.0, "high": 78.0}}, "Tl": {"valence": 13.0, "Ecut_Ry": {"normal": 62.0, "high": 74.0}}, "Pb": {"valence": 14.0, "Ecut_Ry": {"normal": 56.0, "high": 68.0}}, "Bi": {"valence": 15.0, "Ecut_Ry": {"normal": 66.0, "high": 74.0}}, "Po": {"valence": 16.0, "Ecut_Ry": {"normal": 64.0, "high": 76.0}}, "Rn": {"valence": 18.0, "Ecut_Ry": {"normal": 72.0, "high": 84.0}}}

def periodical(structure):
    Z_val = 0 

    '''
    with open('./periodic_table_PBE.json','r') as file:
        periodic_table = json.load(file)
    '''

    Ecut = []
    for i in structure.get_chemical_symbols():
        Z_val += periodic_table[i]['valence']
        Ecut.append(periodic_table[i]['Ecut_Ry']['normal'])

    return Z_val, max(Ecut)

def create_quantumespresso_inputs(structure, bands_gw=None, spin_orbit=False, what = ['scf','nscf']):
    
    '''
    with open('./scf_qe_default.json','r') as file:
        scf = json.load(file)
    with open('./nscf_qe_default.json','r') as file:
        nscf = json.load(file)
    '''
    try:
        Z_valence, Ecut = periodical(structure.get_ase())
    except:
        Z_valence, Ecut = periodical(structure)

    occupied = int(Z_valence/2 + Z_valence%2)

    if not bands_gw:
        bands_gw = occupied*10
        
    scf['SYSTEM']['nbnd'] = int(occupied + 20)
    nscf['SYSTEM']['nbnd'] = int(bands_gw)
    
    scf['SYSTEM']['ecutwfc'] = Ecut
    nscf['SYSTEM']['ecutwfc'] = Ecut

    if Z_valence%2 != 0: 
        scf['SYSTEM']['smearing'] = 'cold'
        nscf['SYSTEM']['smearing'] = 'cold'
        scf['SYSTEM']['occupations'] = 'smearing'
        nscf['SYSTEM']['occupations'] = 'smearing'
        scf['SYSTEM']['degauss'] = 0.02
        nscf['SYSTEM']['degauss'] = 0.02

            
    return scf, nscf


