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
    for i in range(window):
        yambo_calc = conv_workflow.called[-(i+1)].called[-1].called[-1]
        gap[i] = yambo_calc.outputs.array_qp.get_array('Eo')[0]+ \
                 yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]

    conv = True

    for i in range(window):
        if abs(gap[-1]-gap[-i]) > thr: #backcheck
            conv = False

    return conv

'''
def fit_eval(thr, window, fit_type, all_wfls):

    def func(x, a, b,c):
        return a + b/(x-c) #non +...


    popt, pcov = curve_fit(func,gaps_600[:,0],gaps_600[:,1]) #guess
    print('parameters are = ',popt)
'''
'''
def final_plot(conv_workflow):
'''
