# -*- coding: utf-8 -*-
"""Helper functions."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
from collections.abc import Mapping

from aiida.orm import Dict, Str, load_node
from aiida.plugins import CalculationFactory, DataFactory

from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

'''
convergence functions for gw(for now) convergences.
'''

def conv_eval(thr, window, wfl_pk):


    gap = np.zeros(window)
    for i in range(window):
        yambo_calc = load_node(wfl_pk).called[-(i+1)].called[-1].called[-1]
        gap[i] = yambo_calc.outputs.array_qp.get_array('Eo')[0]+ \
                 yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]

    conv = True

    for i in range(window):
        if abs(gap[-1]-gap[-i]) > thr: #backcheck
            conv = False


#def fit_eval(thr, window, fit_type, conv_workflow):

    def func(x, a, b,c):
        return a + b/(x-c) #non +...


    popt, pcov = curve_fit(func,gap[:,0],gap[:,1]) #guess
    #print('parameters are = ',popt)


    if abs(gap[-1]-popt[0]) > thr: #backcheck
            conv = False

    return conv
    #fig, ax = plt.subplots()
    #plt.xlabel(var)
    #plt.ylabel('Gap (eV)')
    #plt.title('600 bands')
    #ax.plot([0,20],[r,r])
    #ax.plot(np.linspace(1,20,100),func(np.linspace(1,20,100),*popt),'-',label='Fit')
    #ax.plot(gaps_1[:,0],gaps_1[:,1],'*-',label='calculated')
    #legend = ax.legend(loc='best', shadow=True)

'''
def final_plot(conv_workflow):
'''
