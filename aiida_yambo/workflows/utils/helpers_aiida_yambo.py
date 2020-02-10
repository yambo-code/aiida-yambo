# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

try:
    from aiida.orm import Dict, Str, load_node, KpointsData, RemoteData
    from aiida.plugins import CalculationFactory, DataFactory
except:
    pass

################################################################################
################################################################################

class calc_manager_aiida_yambo: #the interface class to AiiDA... could be separated fro aiida and yambopy

    def __init__(self, calc_info={}, wfl_type = 'automatic_1D_convergence'):
        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

        self.wfl_type = wfl_type
################################## update_parameters - create parameters space #####################################
    def parameters_space_creator(self, first_calc, last_inputs = {}, k_distance = 1):
        space = []

        if self.wfl_type == 'automatic_1D_convergence':

            for i in range(self.steps):

                if first_calc:
                    first = 0
                else:
                    first = 1

                if self.var == 'kpoints':

                    k_distance = k_distance + self.delta*(first+i)
                    new_value = k_distance

                elif isinstance(self.var,list): #general
                    new_value = []
                    for j in self.var:
                        ind = 0
                        new_params = last_inputs[j]
                        for steps in range(i):
                            new_params = [sum(x) for x in zip(new_params, self.delta[self.var.index(j)])]
                        if first == 1:
                            new_params = [sum(x) for x in zip(new_params, self.delta[self.var.index(j)])]
                        new_value.append(new_params)

                elif isinstance(self.var,str): #general
                    new_params = last_inputs[self.var]
                    new_params = new_params + self.delta*(first+i)
                    new_value = new_params

                space.append((self.var,new_value))

            return space

        elif self.wfl_type == '2D_extrapolation': #pass as input the space

            self.delta = 0
            for step in self.space:
                space.append([self.var,step])

            return space

    def updater(self, inp_to_update, parameters):

        variables = parameters[0]
        new_values = parameters[1]

        if variables == 'kpoints':
            k_distance = new_values

            inp_to_update.scf.kpoints = KpointsData()
            inp_to_update.scf.kpoints.set_cell(inp_to_update.scf.pw.structure.cell)
            inp_to_update.scf.kpoints.set_kpoints_mesh_from_density(1/k_distance, force_parity=True)
            inp_to_update.nscf.kpoints = inp_to_update.scf.kpoints

            try:
                del inp_to_update.parent_folder  #I need to start from scratch...
            except:
                pass

            value = k_distance

        elif isinstance(variables,list): #general
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            for i in variables:
                new_params[i] = new_values[variables.index(i)]

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_values

        elif isinstance(variables,str): #general
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params[variables] = new_values

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_values

        return inp_to_update, value

################################## parsers #####################################
    def take_quantities(self, start = 1): #yambopy wfl_type?

        backtrace = self.steps #*self.iter
        where = self.where
        what = self.what

        print('looking for {} in k-points {}'.format(what,where))

        quantities = np.zeros((len(where),backtrace,3))

        for j in range(len(where)):
            for i in range(1,backtrace+1):
                yambo_calc = load_node(self.wfl_pk).caller.called[backtrace-i].called[0].called[0]
                if what == 'gap':
                    quantities[j,i-1,1] = abs((yambo_calc.outputs.array_ndb.get_array('Eo')[(where[j][1]-1)*2+1].real+
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[(where[j][1]-1)*2+1].real-
                                (yambo_calc.outputs.array_ndb.get_array('Eo')[(where[j][0]-1)*2].real+
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[(where[j][0]-1)*2].real)))*27.2114

                if what == 'single-levels':
                    quantities[j,i-1,1] = abs(yambo_calc.outputs.array_ndb.get_array('Eo')[where[j]-1].real+ \
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[where[j]-1].real)*27.2114

                quantities[j,i-1,0] = i  #number of the iteration times to be used in a fit
                quantities[j,i-1,2] = int(yambo_calc.pk) #CalcJobNode.pk responsible of the calculation

        return quantities


######################### AiiDA specific #############################
    def update_dict(self, _dict, what, how):
        new = _dict.get_dict()
        new[what] = how
        _dict = Dict(dict=new)

    def get_caller(self, calc_pk, depth = 1):
        for i in range(depth):
            calc = load_node(int(calc_pk))
            calc = calc.caller.caller
        return calc

    def get_called(self, calc, depth = 2):
        for i in range(depth):
            calc = calc.called[0]
        return calc

    def start_from_converged(self, inputs, node):
        inputs.yres.gw.parameters = node.get_builder_restart().yres.gw['parameters']

    def set_parent(self, inputs, parent):
        if isinstance(parent, RemoteData):
            inputs.parent_folder = parent
        else:
            inputs.parent_folder = parent.outputs.remote_folder

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
