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
from aiida_yambo.utils.parallelism_finder import *
from aiida_yambo.utils.defaults.create_defaults import *
#we try to use netcdf
try:
    from netCDF4 import Dataset
except ImportError:
    _has_netcdf = False
else:
    _has_netcdf = True
################################################################################
################################################################################

def set_parallelism(instructions_, inputs):

    new_parallelism, new_resources = False, False
    instructions = copy.deepcopy(instructions_)
    resources = inputs.yres.yambo.metadata.options.resources
    structure = inputs.structure.get_ase()
    mesh = inputs.nscf.kpoints.get_kpoints_mesh()[0]
    kpoints = mesh[0]*mesh[1]*mesh[2]/2  #moreless... to fi

    occupied, ecut = periodical(structure)

    bands, qp, last_qp, runlevels = find_gw_info(inputs.yres.yambo)
    
    instructions['automatic'] = instructions.pop('automatic',None)
    instructions['semi-automatic'] = instructions.pop('semi-automatic',None)
    instructions['manual'] = instructions.pop('manual',None)
    instructions['function'] = instructions.pop('function',None)

    if 'BndsRnXp' in inputs.yres.yambo.parameters.get_dict()['variables'].keys():
        yambo_bandsX = inputs.yres.yambo.parameters.get_dict()['variables']['BndsRnXp'][0][-1]
    else:
        yambo_bandsX = 0 
    
    if 'GbndRnge' in inputs.yres.yambo.parameters.get_dict()['variables'].keys():
        yambo_bandsSc = inputs.yres.yambo.parameters.get_dict()['variables']['GbndRnge'][0][-1]
    else:
        yambo_bandsSc = 0
    
    if 'NGsBlkXp' in inputs.yres.yambo.parameters.get_dict()['variables'].keys():
        yambo_cutG = inputs.yres.yambo.parameters.get_dict()['variables']['NGsBlkXp'][0]
    else:
        yambo_cutG = 0

    bands = max(yambo_bandsX,yambo_bandsSc)

    if instructions['automatic'] and ('gw0' or 'HF_and_locXC' in runlevels):
        #standard
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine'], \
                                                        resources['num_cores_per_mpiproc'], bands, \
                                                        occupied, qp, kpoints,\
                                                        last_qp, namelist = {})
    
    elif instructions['semi-automatic'] and ('gw0' or 'HF_and_locXC' in runlevels):
        #parallel set for boundaries of params
        #also, specification of the number of nodes
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine'], \
                                                        resources['num_cores_per_mpiproc'], bands, \
                                                        occupied, qp, kpoints,\
                                                        last_qp, namelist = {})
    
    elif instructions['manual']:
        #parallel set for each set of params
        #specification of all the parameters and resources
        # 
        #main parameters...
        for i in instructions['manual'].keys():
            BndsRnXp_hint = instructions['manual'][i].pop('BndsRnXp', [0])
            GbndRnge_hint = instructions['manual'][i].pop('GbndRnge', [0])
            NGsBlkXp_hint = instructions['manual'][i].pop('NGsBlkXp', [0])
            kpoints_hint = instructions['manual'][i].pop('kpoints', [0])

            X = (yambo_bandsX >= min(BndsRnXp_hint) and yambo_bandsX <= max(BndsRnXp_hint)) or len(BndsRnXp_hint)==1 
            Sc = (yambo_bandsSc >= min(GbndRnge_hint) and yambo_bandsX <= max(GbndRnge_hint)) or len(GbndRnge_hint)==1 
            G = (yambo_cutG >= min(NGsBlkXp_hint) and yambo_cutG <= max(NGsBlkXp_hint)) or len(NGsBlkXp_hint)==1 
            K = (kpoints >= min(kpoints_hint) and kpoints <= max(kpoints_hint)) or len(kpoints_hint)==1 
            if X and Sc and G and K:
                new_parallelism = instructions['manual'][i]['parallelism']
                new_resources = instructions['manual'][i]['resources']
                break
            else: 
                pass
        
        #new_parallelism = instructions['manual']['parallelism']
        #new_resources = instructions['manual']['resources']
    
    elif instructions['function']:
        pass

    else:
        return False, False

    return new_parallelism, new_resources


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
    
    if calc_dict['type'] != '1D_convergence': 
        calc_dict['steps'] = len(calc_dict['space'])
    
    return calc_dict

################################## update_parameters - create parameters space #####################################
def updater(calc_dict, inp_to_update, parameters, workflow_dict):
    
    already_done = False
    values_dict = {}
    parallelism_instructions = workflow_dict['parallelism_instructions']

    if not isinstance(calc_dict['var'],list):
        calc_dict['var'] = [calc_dict['var']]

    input_dict = copy.deepcopy(inp_to_update.yres.yambo.parameters.get_dict())
    
    for var in calc_dict['var']:
        
        if var == 'kpoint_mesh' or var == 'kpoint_density':
            k_quantity = parameters[var].pop(0)
            k_quantity_shift = inp_to_update.nscf.kpoints.get_kpoints_mesh()[1]

            inp_to_update.nscf.kpoints = KpointsData()
            inp_to_update.nscf.kpoints.set_cell_from_structure(inp_to_update.structure) #to count the PBC...
            if isinstance(k_quantity,tuple) or isinstance(k_quantity,list):
                inp_to_update.nscf.kpoints.set_kpoints_mesh(k_quantity,k_quantity_shift) 
            else:
                inp_to_update.nscf.kpoints.set_kpoints_mesh_from_density(1/k_quantity, force_parity=True)

            try:
                inp_to_update.parent_folder =  find_pw_parent(take_calc_from_remote(inp_to_update.parent_folder), calc_type=['scf']).outputs.remote_folder 
                #I need to start from the scf calc
            except:
                if hasattr(inp_to_update, 'parent_folder'): del inp_to_update.parent_folder #do all scf+nscf+y in case

            inp_to_update.yres.yambo.settings = update_dict(inp_to_update.yres.yambo.settings, 'COPY_SAVE', False) #no yambo here
            inp_to_update.yres.yambo.settings = update_dict(inp_to_update.yres.yambo.settings, 'COPY_DBS', False)  #no yambo here
            values_dict[var]=k_quantity
        else:
            input_dict['variables'][var] = parameters[var].pop(0)
            inp_to_update.yres.yambo.parameters = Dict(dict=input_dict)
            values_dict[var]=input_dict['variables'][var]

    #if len(parallelism_instructions.keys()) >= 1:
    new_para, new_res = set_parallelism(parallelism_instructions, inp_to_update)

    if new_para and new_res:
        inp_to_update.yres.yambo.parameters = update_dict(inp_to_update.yres.yambo.parameters, list(new_para.keys()), 
                                                        list(new_para.values()),sublevel='variables')
        inp_to_update.yres.yambo.metadata.options.resources = new_res
        try:
            inp_to_update.yres.yambo.metadata.options.prepend_text = "export OMP_NUM_THREADS="+str(new_res['num_cores_per_mpiproc'])
        except:
            pass
    
    already_done, parent_nscf, parent_scf = search_in_group(inp_to_update, 
                                               workflow_dict['group'])
    
    if parent_nscf and not hasattr(inp_to_update, 'parent_folder'):
        try:
            inp_to_update.parent_folder =  load_node(parent_nscf).outputs.remote_folder 
        except:
            pass
    elif parent_scf:
        try:
            inp_to_update.parent_folder =  load_node(parent_nscf).outputs.remote_folder 
        except:
            pass

    return inp_to_update, values_dict, already_done, parent_nscf

################################## parsers #####################################
def take_quantities(calc_dict, workflow_dict, steps = 1, what = ['gap_eV'], backtrace=1):

    parameter_names = list(workflow_dict['parameter_space'].keys())
    
    backtrace = calc_dict['steps'] 
    what = workflow_dict['what']

    l_iter = []
    for i in range(1,backtrace+1):
        l_calc = []
        ywf_node = load_node(workflow_dict['wfl_pk'][backtrace-i])
        for n in parameter_names:
            try:
                if 'mesh' in n:
                    value = ywf_node.inputs.nscf__kpoints.get_kpoints_mesh()[0]
                else:
                    value = ywf_node.inputs.yres__yambo__parameters.get_dict()['variables'][n][0]
            except:
                value = 0
            l_calc.append(value)
            
        for j in range(len(what)):        
            if ywf_node.is_finished_ok:
                quantity = ywf_node.outputs.output_ywfl_parameters.get_dict()[what[j]]
                l_calc.append(quantity)
            else:
                quantity = False
                l_calc.append(quantity)           
            
        l_calc.append(ywf_node.uuid)
        l_iter.append(l_calc)
    
    quantities = pd.DataFrame(l_iter, columns = parameter_names + what + ['uuid'])

    return quantities

def start_from_converged(inputs, node_uuid,):
    node = load_node(node_uuid)
    inputs.yres.yambo.parameters = node.called[0].get_builder_restart().yambo['parameters']
    inputs.yres.yambo.metadata.options.resources = node.called[0].called[0].get_options()['resources']
    inputs.yres.yambo.metadata.options.max_wallclock_seconds = node.called[0].called[0].get_options()['max_wallclock_seconds']