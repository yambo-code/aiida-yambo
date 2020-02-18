# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
except:
    pass

################################################################################
################################################################################

class calc_manager_aiida_qe: #the interface class to AiiDA... could be separated fro aiida and yambopy

    def __init__(self, calc_info={}):
        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

################################## update_parameters #####################################
    def updater(self, inp_to_update, k_distance, first):    #parameter list? yambopy philosophy

        if self.var == 'bands':
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params['BndsRnXp'][-1] = new_params['BndsRnXp'][-1] + self.delta*first
            new_params['GbndRnge'][-1] = new_params['GbndRnge'][-1] + self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params['GbndRnge'][-1]

        elif self.var == 'kpoints':
            k_distance = k_distance + self.delta*first

            inp_to_update.scf.kpoints = KpointsData()
            inp_to_update.scf.kpoints.set_cell(inp_to_update.scf.pw.structure.cell)
            inp_to_update.scf.kpoints.set_kpoints_mesh_from_density(1/k_distance, force_parity=True)
            inp_to_update.nscf.kpoints = inp_to_update.scf.kpoints

            try:
                del inp_to_update.parent_folder  #I need to start from scratch...
            except:
                pass

            value = k_distance

        elif self.var == 'cutoff':
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params['CUTBox'] = new_params['CUTBox'] + [1,1,1]*self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params['CUTBox'][-1]

        else: #"scalar" quantity
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params[str(self.var)] = new_params[str(self.var)] + self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params[str(self.var)]

        return inp_to_update, value

################################## parsers #####################################
    def take_quantities(self, start = 1): #yambopy philosophy?

        backtrace = self.steps #*self.iter
        what = self.what

        print('looking for {} in k-points {}'.format(what,where))

        if what == 'etot':

            etot = np.zeros((calcs_info['steps']*calcs_info['iter'],3))
            for i in range(1,calcs_info['steps']*calcs_info['iter']+1):
                pw_calc = load_node(calcs_info['wfl_pk']).caller.called[calcs_info['steps']*calcs_info['iter']-i].called[0]
                etot[i-1,1] = pw_calc.outputs.output_parameters.get_dict()['energy']
                etot[i-1,0] = i*calcs_info['delta']  #number of the iteration times the delta... to be used in a fit
                etot[i-1,2] = int(pw_calc.pk) #calc responsible of the calculation

            return etot #delta etot better?

        elif what == 'structure':

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


######################### AiiDA specific #############################

    def get_caller(self, calc, depth = 2):
        for i in range(depth):
            calc = load_node(calc).caller
        return calc

    def get_called(self, calc, depth = 2):
        for i in range(depth):
            calc = load_node(calc).called[0]
        return calc

    def start_from_converged(self, node, params):
        self.ctx.calc_inputs.pw.parameters = node.get_builder_restart().pw['parameters']

    def set_relaxed_structure(self, last_ok):
        self.ctx.calc_inputs.pw.structure = last_ok.outputs.output_structure

    def set_parent(self, last_ok):
        self.ctx.calc_inputs.pw.parent_folder = last_ok.called[0].outputs.remote_folder

    def take_down(self, node = 0, what = 'CalcJobNode'):

        global calc_node

        if node == 0:
            node = load_node(self.wfl_pk)
        else:
            node = load_node(node)

        if what not in str(node.get_description):
            self.take_down(node.called[0])
        else:
            calc_node = node

        return calc_node

    def take_super(self, node = 0, what = 'WorkChainNode'):

        global workchain_node

        if node == 0:
            node = load_node(self.wfl_pk)
        else:
            node = load_node(node)

        if what not in str(node.get_description):
            self.take_super(node.caller)
        else:
            workchain_node = node

        return workchain_node
