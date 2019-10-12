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

def take_gw_gap(calcs_info,k_density):

    gap = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
    for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
        yambo_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0].called[0]
        gap[i-1,1] = abs((yambo_calc.outputs.array_qp.get_array('Eo')[1]+
                    yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[1])-
                   (yambo_calc.outputs.array_qp.get_array('Eo')[0]+
                    yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]))
        if calcs_info['var']=='kpoints':
            gap[i-1,0] = i+k_density
        else:
            gap[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
        gap[i-1,2] = int(yambo_calc.pk) #calc responsible of the calculation

    return gap

def take_qe_total_energy(calcs_info,k_density):

    etot = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
    for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
        pw_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0]
        etot[i-1,1] = pw_calc.outputs.output_parameters.get_dict()['energy']
        if calcs_info['var']=='kpoints':
            etot[i-1,0] = i+k_density
        else:
            etot[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
        etot[i-1,2] = int(pw_calc.pk) #calc responsible of the calculation

    return etot #delta etot better?


def convergence_evaluation(calcs_info,to_conv_quantity):

    conv = True

    for i in range(calcs_info['conv_window']):
        if abs(to_conv_quantity[-1,1]-to_conv_quantity[-(i+1),1]) > calcs_info['conv_thr']: #backcheck
            conv = False

    '''
    #if calcs_info['conv_options']['fit'] == 'yes'
    def func(x, a, b,c):
        return a + b/(x-c) #non +...
    try:
        try:
           popt, pcov = curve_fit(func, gap[:,0], gap[:,1]) #guess
           if abs(gap[-1,1]-popt[0]) > calcs_info['conv_thr']: #backcheck
                   conv = False
        except:
           popt, pcov = curve_fit(func, gap[-calcs_info['steps']:,0], gap[-calcs_info['steps']:,1])
           if abs(gap[-1,1]-popt[0]) > calcs_info['conv_thr']: #backcheck
                   conv = False
    except:
        popt=[]
        popt.append('fit not succesful')
    '''

    return conv, to_conv_quantity[-calcs_info['steps']:,:] #, popt[0]

def last_conv_calc_recovering(calcs_info,last_val,what):

    i = calcs_info['conv_window']
    have_to_backsearch = True
    while have_to_backsearch:
        try:
            calc = load_node(calcs_info['wfl_pk']).caller.called[i].called[0]
            if what == 'energy':
                value = calc.outputs.output_parameters.get_dict()[str(what)]
            else:
                value = abs((calc.called[0].outputs.array_qp.get_array('Eo')[1]+
                            calc.called[0].outputs.array_qp.get_array('E_minus_Eo')[1])-
                           (calc.called[0].outputs.array_qp.get_array('Eo')[0]+
                            calc.called[0].outputs.array_qp.get_array('E_minus_Eo')[0]))

            if abs(value-last_val) < calcs_info['conv_thr']:
                have_to_backsearch = True
                i +=1
            elif abs(value-last_val) >= calcs_info['conv_thr']:
                have_to_backsearch = False #this is the first out of conv
        except:
            have_to_backsearch = False
            i = calcs_info['conv_window']

    last_conv_calc = load_node(calcs_info['wfl_pk']).caller.called[i-1].pk #last wfl ok

    return  int(last_conv_calc), i







'''
def final_plot(conv_workflow):
'''
