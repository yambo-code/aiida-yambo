# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

try:
    from aiida.orm import Dict, Str, load_node, KpointsData, RemoteData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
except:
    pass

#we try to use netcdf
try:
    from netCDF4 import Dataset
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True
################################################################################
################################################################################

class calc_manager_aiida_yambo: #the interface class to AiiDA... could be separated fro aiida and yambopy

    def __init__(self, calc_info={}, wfl_settings={}):
        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

        for key in wfl_settings.keys():
            setattr(self, str(key), wfl_settings[key])

################################## update_parameters - create parameters space #####################################
    def parameters_space_creator(self, first_calc, parent, last_inputs = {}):
        space = []

        if self.type == '1D_convergence':

            if self.var == 'kpoints':

                k_distance = get_distance_from_kmesh(find_pw_parent(parent))

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

        elif self.type == '2D_space': #pass as input the space; actually, it's n-dimensional

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
                inp_to_update.parent_folder = find_pw_parent(inp_to_update.parent_folder.get_incoming().get_node_by_label('remote_folder'),\
                                                            calc_type='scf').outputs.remote_folder  #I need to start from the scf calc
            except:
                pass

            inp_to_update.yres.gw.settings = update_dict(inp_to_update.yres.gw.settings, 'HARD_LINK', False)

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
    def take_quantities(self, start = 1):

        backtrace = self.steps #*self.iter
        where = self.where
        what = self.what

        print('looking for {} in k-points {}'.format(what,where))

        quantities = np.zeros((len(where),backtrace,3))

        for j in range(len(where)):
            for i in range(1,backtrace+1):
                yambo_calc = load_node(self.wfl_pk).caller.called[backtrace-i].called[0].called[0]
                if what == 'gap':
                    _vb=find_table_ind(where[j][1], where[j][0],yambo_calc.outputs.array_ndb)
                    _cb=find_table_ind(where[j][3], where[j][2],yambo_calc.outputs.array_ndb)
                    quantities[j,i-1,1] = abs((yambo_calc.outputs.array_ndb.get_array('Eo')[_vb].real+
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real)-
                                (yambo_calc.outputs.array_ndb.get_array('Eo')[_cb].real+
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[_cb].real))

                if what == 'single-levels':
                    _level=find_table_ind(where[j][1], where[j][0],yambo_calc.outputs.array_ndb)
                    quantities[j,i-1,1] = yambo_calc.outputs.array_ndb.get_array('Eo')[_level].real+ \
                                yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')[_level].real

                quantities[j,i-1,1] = quantities[j,i-1,1]*27.2114
                quantities[j,i-1,0] = i  #number of the iteration times to be used in a fit
                quantities[j,i-1,2] = int(yambo_calc.pk) #CalcJobNode.pk responsible of the calculation

        return quantities

    def start_from_converged(self, inputs, node):
         inputs.yres.gw.parameters = node.get_builder_restart().yres.gw['parameters']
