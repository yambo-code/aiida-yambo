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

#class calc_manager_aiida_yambo: 
def calc_manager_aiida_yambo(calc_info={}, wfl_settings={}):
    
    calc_dict = {}
    calc_dict.update(calc_info)
    calc_dict.update(wfl_settings)
    calc_dict['iter']  = 0
    calc_dict['success'] = False
    calc_dict['conv_thr'] = calc_dict.pop('conv_thr',0.1)
    calc_dict['max_iterations'] = calc_dict.pop('max_iterations',3)
    calc_dict['steps'] = calc_dict.pop('steps',3)
    calc_dict['conv_window'] = calc_dict.pop('conv_window',calc_dict['steps'])
    calc_dict['offset'] = calc_dict.pop('offset',0)
    
    return calc_dict

################################## update_parameters - create parameters space #####################################
def parameters_space_creator(calc_dict, first_calc, parent, last_inputs = {}):
    space = []

    if calc_dict['type'] == '1D_convergence':
        
        k_distance_old = None
        
        if calc_dict['var'] == 'kpoint_mesh' or calc_dict['var'] == 'kpoint_density':

            k_distance_old = get_distance_from_kmesh(find_pw_parent(parent, calc_type=['nscf','scf']))
            k_mesh_old = find_pw_parent(parent, calc_type=['nscf','scf']).inputs.kpoints.get_kpoints_mesh()
        
        elif not isinstance(calc_dict['var'],list):
            
            calc_dict['var'] = calc_dict['var'].split(',')

        for i in range(calc_dict['steps']):

            if first_calc:
                first = 0
            else:
                first = 1

            if calc_dict['var'] == 'kpoint_density' and k_distance_old:
                if isinstance(calc_dict['delta'],list):
                    calc_dict['delta'] = calc_dict['delta'][0]

                k_distance = k_distance_old + calc_dict['delta']*(first+i)
                new_value = k_distance
                            
            elif (calc_dict['var'] == 'kpoint_mesh') or (calc_dict['var'] == 'kpoint_density' and not k_distance_old):
                if not isinstance(calc_dict['delta'],list):
                    calc_dict['delta'] = 3*[calc_dict['delta']]
                k_mesh_0 = k_mesh_old[0]
                k_mesh_1 = k_mesh_old[1]
                #for k in range(i+first):
                k_mesh_0 = [sum(x) for x in zip(k_mesh_0, [l*(first+i) for l in calc_dict['delta']])]
                k_mesh_1 = k_mesh_old[1]
                k_mesh = (k_mesh_0,k_mesh_1)
                new_value = k_mesh

            elif isinstance(calc_dict['var'],list): #general
                new_value = []
                for j in calc_dict['var']:
                    new_params = last_inputs[j]
                    
                    #for steps in range(i+first):
                    if isinstance(calc_dict['delta'],int):
                        new_params = new_params + calc_dict['delta']*(i+first)

                    elif isinstance(calc_dict['delta'][calc_dict['var'].index(j)],list):
                        new_params = [sum(x) for x in zip(new_params, [l*(i+first) for l in calc_dict['delta'][calc_dict['var'].index(j)]])]  

                    elif not isinstance(calc_dict['delta'][calc_dict['var'].index(j)],list) and not isinstance(new_params,list):
                        new_params = new_params + calc_dict['delta'][calc_dict['var'].index(j)]*(i+first)

                    elif isinstance(new_params,list):
                        for k in range(len(new_params)):
                            new_params = [sum(x) for x in zip(new_params, [l*(i+first) for l in calc_dict['delta']])]
                    else:
                        new_params = new_params + calc_dict['delta']*(i+first)
            
                    new_value.append(new_params)

            space.append((calc_dict['var'],new_value))

        return space

    elif calc_dict['type'] == '2D_space': #pass as input the space; actually, it's n-dimensional

        calc_dict['delta'] = 0
        for step in calc_dict['space']:
            space.append([calc_dict['var'],step])

        return space

def updater(calc_dict, inp_to_update, parameters):

    variables = parameters[0]
    new_values = parameters[1]

    if variables == 'kpoint_mesh' or variables == 'kpoint_density':
        k_quantity = new_values

        inp_to_update.scf.kpoints = KpointsData()
        inp_to_update.scf.kpoints.set_cell_from_structure(inp_to_update.scf.pw.structure) #to count the PBC...
        if isinstance(k_quantity,tuple):
            inp_to_update.scf.kpoints.set_kpoints_mesh(k_quantity[0],k_quantity[1]) 
        else:
            inp_to_update.scf.kpoints.set_kpoints_mesh_from_density(1/k_quantity, force_parity=True)
        inp_to_update.nscf.kpoints = inp_to_update.scf.kpoints

        try:
            inp_to_update.parent_folder =  find_pw_parent(take_calc_from_remote(inp_to_update.parent_folder), calc_type=['scf']).outputs.remote_folder 
            #I need to start from the scf calc
        except:
            del inp_to_update.parent_folder #do all scf+nscf+y in case

        inp_to_update.yres.yambo.settings = update_dict(inp_to_update.yres.yambo.settings, 'COPY_SAVE', False) #no yambo here
        inp_to_update.yres.yambo.settings = update_dict(inp_to_update.yres.yambo.settings, 'COPY_DBS', False)  #no yambo here

        value = k_quantity

    elif isinstance(variables,list): #general
        new_params = inp_to_update.yres.yambo.parameters.get_dict()
        for i in variables:
            new_params[i] = new_values[variables.index(i)]

        inp_to_update.yres.yambo.parameters = Dict(dict=new_params)

        value = new_values

    elif isinstance(variables,str): #general
        new_params = inp_to_update.yres.yambo.parameters.get_dict()
        if isinstance(new_values,list):
            new_params[variables] = new_values[0]
        else:
            new_params[variables] = new_values

        inp_to_update.yres.yambo.parameters = Dict(dict=new_params)

        value = new_values

    return inp_to_update, value

################################## parsers #####################################
def take_quantities(calc_dict, steps = 1, where = [], what = 'gap',backtrace=1):

    try:
        backtrace = calc_dict['steps'] 
        where = calc_dict['where']
        what = calc_dict['what']
    except:
        pass

    print('looking for {} in k-points {}'.format(what,where))

    quantities = np.zeros((len(where),backtrace,3))

    for j in range(len(where)):
        for i in range(1,backtrace+1):
            try: #YamboConvergence
                yambo_calc = load_node(calc_dict['wfl_pk']).caller.called[backtrace-i].called[0].called[0]
            except: #YamboWorkflow,YamboRestart of YamboCalculation
                yambo_calc = load_node(calc_dict['wfl_pk'])
                print('values provided are: [iteration, value in eV, workflow pk]')
            if yambo_calc.is_finished_ok:
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
            else:
                quantities[j,i-1,1] = False
                
            quantities[j,i-1,0] = i  #number of the iteration times to be used in a fit
            quantities[j,i-1,2] = int(yambo_calc.pk) #CalcJobNode.pk responsible of the calculation

    return quantities

def start_from_converged(inputs, node,):
    inputs.yres.yambo.parameters = node.called[0].get_builder_restart().yambo['parameters']
    inputs.yres.yambo.metadata.options.resources = node.called[0].called[0].get_options()['resources']
    inputs.yres.yambo.metadata.options.max_wallclock_seconds = node.called[0].called[0].get_options()['max_wallclock_seconds']