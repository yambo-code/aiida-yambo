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
 convergence functions .
'''

def take_gw_gap(calcs_info):

    gap = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
    for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
        yambo_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0].called[0]
        gap[i-1,1] = abs((yambo_calc.outputs.array_qp.get_array('Eo')[1]+
                    yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[1])-
                   (yambo_calc.outputs.array_qp.get_array('Eo')[0]+
                    yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]))
        gap[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
        gap[i-1,2] = int(yambo_calc.pk) #calc responsible of the calculation

    return gap

def take_qe_total_energy(calcs_info):

    etot = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
    for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
        pw_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0]
        etot[i-1,1] = pw_calc.outputs.output_parameters.get_dict()['energy']
        etot[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
        etot[i-1,2] = int(pw_calc.pk) #calc responsible of the calculation

    return etot #delta etot better?

def take_relaxation_params(calcs_info):

    etot = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
    cells = np.zeros((calcs_info['steps']*calcs_info['iter'],3,3))
    nr_atoms = load_node(calcs_info['wfl_pk']).caller.called[0].called[0].outputs.output_parameters.get_dict()['number_of_atoms']
    atoms = np.zeros((calcs_info['steps']*calcs_info['iter'],nr_atoms,3))

    for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
        pw_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0]
        etot[i-1,1] = pw_calc.outputs.output_parameters.get_dict()['energy']
        etot[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
        etot[i-1,2] = int(pw_calc.pk) #calc responsible of the calculation
        cells[i-1] = np.matrix(pw_calc.outputs.output_structure.cell)


        for j in range(nr_atoms):
                atoms[i-1][j] = np.array(pw_calc.outputs.output_structure.sites[j].position)

    return [etot, cells, atoms] #delta etot better?

def conv_vc_evaluation(calcs_info,params):

    etot = params[0]
    cells = params[1]
    atoms = params[2]
    relaxed = False

    for i in range(calcs_info['conv_window']):


        if np.max(abs(cells[-1]-cells[-(i+1)])) < calcs_info['conv_thr_cell']: #backcheck
            for j in range(len(atoms[1])):
                if np.max(abs(atoms[-1][j]-atoms[-(i+1)][j]))  < calcs_info['conv_thr_atoms']: #backcheck
                    relaxed = True
                else:
                    relaxed = False

        else:
            relaxed = False


    return relaxed, etot[-calcs_info['steps']:,:]


def last_relax_calc_recovering(calcs_info,last_params):

    last_conv = calcs_info['steps'] # steps e window vanno uguali
    letot = last_params[0]
    lcells = last_params[1]
    latoms = last_params[2]


    for i in range(calcs_info['steps']+1, calcs_info['iter']*calcs_info['steps']+2):
        try:
            if i == calcs_info['iter']*calcs_info['steps']+1:
                etot = load_node(last_conv_story[-(calcs_info['iter']*calcs_info['steps']+1)][-2]).outputs.output_parameters.get_dict()['energy']
                cells = load_node(last_conv_story[-(calcs_info['iter']*calcs_info['steps']+1)][-2]).outputs.output_structure.cell
                nr_atoms = load_node(last_conv_story[-(calcs_info['iter']*calcs_info['steps']+1)][-2]).outputs.output_parameters.get_dict()['number_of_atoms']

                for j in range(len(atoms)):
                    if np.max(abs(cells-lcells)) < calcs_info['conv_thr_cell'] and \
                    np.max(abs(atoms[j]-latoms[j])) < calcs_info['conv_thr_atoms']:
                        last_conv_calc = load_node(last_conv_story[-2]).caller.caller.pk
                else:
                    break
            else:
                pw_calc = load_node(calcs_info['wfl_pk']).caller.called[i-1].called[0]
                etot = pw_calc.outputs.output_parameters.get_dict()['energy']
                cells = pw_calc.outputs.output_structure.cell
                nr_atoms = pw_calc.outputs.output_parameters.get_dict()['number_of_atoms']
                for j in range(len(atoms)):
                    if np.max(abs(cells-lcells)) < calcs_info['conv_thr_cell'] and \
                    np.max(abs(atoms[j]-latoms[j])) < calcs_info['conv_thr_atoms']:
                        last_conv = i
                    else: #backcheck
                        break
        except:
            last_conv = calcs_info['steps']
            break

    last_conv_calc_pk = load_node(calcs_info['wfl_pk']).caller.called[last_conv-1].pk #last wfl ok

    return  int(last_conv_calc_pk), last_conv-1



def convergence_evaluation(calcs_info,to_conv_quantity):

    conv = True

    for i in range(calcs_info['conv_window']):
        if abs(to_conv_quantity[-1,1]-to_conv_quantity[-(i+1),1]) > calcs_info['conv_thr']: #backcheck
            conv = False

    return conv, to_conv_quantity[-calcs_info['steps']:,:] #, popt[0]



def last_conv_calc_recovering(calcs_info,last_val,what,last_conv_story):

    last_conv = calcs_info['steps']
    last_conv_calc = load_node(calcs_info['wfl_pk']).caller.called[last_conv-1].pk #last wfl ok

    for i in range(calcs_info['steps']+1, calcs_info['iter']*calcs_info['steps']+2):

        try:
            if i == calcs_info['iter']*calcs_info['steps']+1:
                value = last_conv_story[-(calcs_info['iter']*calcs_info['steps']+1)][-3]
                if abs(value-last_val) < calcs_info['conv_thr']:
                    last_conv_calc = load_node(last_conv_story[-2]).caller.caller.pk
                else:
                    break
            else:
                calc = load_node(calcs_info['wfl_pk']).caller.called[i-1].called[0]
                if what == 'energy':
                    value = calc.outputs.output_parameters.get_dict()[str(what)]
                else:
                    value = abs((calc.called[0].outputs.array_qp.get_array('Eo')[1]+
                                calc.called[0].outputs.array_qp.get_array('E_minus_Eo')[1])-
                               (calc.called[0].outputs.array_qp.get_array('Eo')[0]+
                                calc.called[0].outputs.array_qp.get_array('E_minus_Eo')[0]))

                if abs(value-last_val) < calcs_info['conv_thr']:
                    last_conv = i
                    last_conv_calc = load_node(calcs_info['wfl_pk']).caller.called[last_conv-1].pk #last wfl ok
                else:
                    break
        except:
            last_conv = calcs_info['steps']
            break


    return  int(last_conv_calc), last_conv-1







'''
def final_plot(conv_workflow):
'''
