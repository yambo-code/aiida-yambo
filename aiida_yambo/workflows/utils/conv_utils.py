# -*- coding: utf-8 -*-
"""Helper functions."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from collections.abc import Mapping

from aiida.orm import Dict, Str
from aiida.plugins import CalculationFactory, DataFactory

from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

'''
convergence functions for gw convergences.
'''

def conv_eval(thr, window, conv_workflow):

    gap = np.zeros(window)
    for i in range(1, window):
        yambo_calc = workflows[-i].called[-1].called[-1]
        gap[i-1] = yambo_calc.outputs.array_qp.get_array('Eo')[0]+ \
                 yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]

    if (abs(gap[-1]-gap[i]) > thr for i in range(1,window)):
        return False
    else:
        return True


'''
def fit_eval(thr, window, fit_type, all_wfls):

    def func(x, a, b,c):
        return a + b/(x-c) #non +...


    popt, pcov = curve_fit(func,gaps_600[:,0],gaps_600[:,1]) #guess
    print('parameters are = ',popt)
'''
