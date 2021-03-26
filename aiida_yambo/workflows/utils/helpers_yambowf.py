# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import cmath

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
    from aiida_yambo.utils.parallelism_finder import *
except:
    pass

from aiida_yambo.utils.defaults.create_defaults import *

def quantumespresso_input_validator(workchain_inputs,):
    
    messages = []

    yambo_bandsX = workchain_inputs.yres.yambo.parameters.get_dict()['variables'].pop('BndsRnXp',[[0],''])[0][-1]
    yambo_bandsSc = workchain_inputs.yres.yambo.parameters.get_dict()['variables'].pop('GbndRnge',[[0],''])[0][-1]
    gwbands = max(yambo_bandsX,yambo_bandsSc)
    message_bands = 'GW bands are: {} '.format(gwbands)
    messages.append(message_bands)
    scf_params_def, nscf_params_def = create_quantumespresso_inputs(workchain_inputs.structure, bands_gw = gwbands)

    if hasattr(workchain_inputs,'parent_folder'):
        parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
        try:
            scf_params_parent = find_pw_parent(parent_calc, calc_type=['scf']).inputs.parameters
            message_scf_parent = 'found scf inputs from parent'
        except:
            scf_params_parent = False
    else:
        scf_params_parent = False

    if hasattr(workchain_inputs,'parent_folder'):
        parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
        try:
            nscf_params_parent = find_pw_parent(parent_calc, calc_type=['nscf']).inputs.parameters
            message_nscf_parent = 'found nscf inputs from parent'
        except:
            nscf_params_parent = False
    else:
        nscf_params_parent = False

    if scf_params_parent:
        message_scf = message_scf_parent
        messages.append(message_scf)
        scf_params =  scf_params_parent 
    elif hasattr(workchain_inputs,'scf_parameters'):
        message_scf = 'scf inputs found'
        messages.append(message_scf)
        scf_params =  workchain_inputs.scf_parameters       
    else:
        message_scf = 'scf inputs not found, setting defaults'
        messages.append(message_scf)
        scf_params = scf_params_def
        scf_params['SYSTEM']['nbnd'] = int(scf_params_def['SYSTEM']['nbnd'])
        scf_params = Dict(dict=scf_params)
    
    redo_nscf = False
        
    if nscf_params_parent:
        message_nscf = message_nscf_parent
        messages.append(message_nscf)
        nscf_params =  nscf_params_parent
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += 'setting nbnd of the nscf calculation to b = {}'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
            messages.append(message_nscf)  
    elif hasattr(workchain_inputs,'nscf_parameters'):
        message_nscf = 'nscf inputs found' 
        nscf_params =  workchain_inputs.nscf_parameters
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += ', and setting nbnd of the nscf calculation to b = {}'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf)       
    else:
        message_nscf = 'nscf inputs not found, setting defaults'
        nscf_params = copy.deepcopy(scf_params.get_dict())
        nscf_params['CONTROL']['calculation'] = nscf_params_def['CONTROL']['calculation']
        nscf_params['SYSTEM']['nbnd'] = int(gwbands)
        nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf)
    
            
    if 'defaults' in message_scf:
        message_scf_corr='setting scf defaults according to nscf'
        messages.append(message_scf_corr)
        scf_params = copy.deepcopy(scf_params.get_dict())
        bands_scf = scf_params['SYSTEM']['nbnd']
        scf_params['SYSTEM'] = copy.deepcopy(nscf_params['SYSTEM'])
        scf_params['CONTROL']['calculation'] = 'scf'
        scf_params['SYSTEM']['nbnd'] = int(bands_scf)
        scf_params = Dict(dict=scf_params)
    '''
    elif 'parent' in message_scf and not 'defaults' in message_nscf and not 'parents' in message_nscf:
        message_nscf_corr = 'nscf inputs from scf parent'
        bands = nscf_params.get_dict()['SYSTEM']['nbnd']
        nscf_params = scf_params.get_dict()
        nscf_params['CONTROL']['calculation'] = 'nscf'
        nscf_params['SYSTEM']['nbnd'] = int(bands)
        nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf_corr)
    '''

    
    return scf_params, nscf_params, redo_nscf, gwbands, messages 

def add_corrections(workchain_inputs, additional_parsing_List):
    
    parsing_List = additional_parsing_List
    qp_list = []
    #take mapping from nscf
    parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
    try:
        nscf = find_pw_parent(parent_calc, calc_type=['nscf'])
    except:
        nscf = parent_calc
    mapping = gap_mapping_from_nscf(nscf.pk, additional_parsing_List)
    val = mapping['valence']
    cond = mapping['conduction'] 
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']
    
    new_params = workchain_inputs.yambo.parameters.get_dict()
    new_params['variables']['QPkrange'] = new_params['variables'].pop('QPkrange', [[],''])

    for name in parsing_List:

        if isinstance(name,list) and name[0] in mapping.keys():
            for i in mapping[name[0]]:
                if not i in new_params['variables']['QPkrange'][0]: new_params['variables']['QPkrange'][0].append(i) 
        elif isinstance(name,str) and name in mapping.keys():
            for i in mapping[name]:
                if not i in new_params['variables']['QPkrange'][0]: new_params['variables']['QPkrange'][0].append(i) 
    
        elif name == 'homo' in parsing_List:
           if not [homo_k, homo_k, val,val] in new_params['variables']['QPkrange'][0]: new_params['variables']['QPkrange'][0].append([homo_k, homo_k, val,val])
    
        elif name == 'lumo' in parsing_List:
            if not [lumo_k,lumo_k, cond,cond] in new_params['variables']['QPkrange'][0]: new_params['variables']['QPkrange'][0].append([lumo_k,lumo_k, cond,cond])
    
    return mapping, Dict(dict=new_params)

def parse_qp_level(calc, level_map):

    _vb=find_table_ind(level_map[2], level_map[1], calc.outputs.array_ndb)
    level_dft = calc.outputs.array_ndb.get_array('Eo')[_vb].real
    level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real

    level_gw = (level_dft + level_corr)*27.2114

    return level_gw

def parse_qp_gap(calc, gap_map):

    _vb=find_table_ind(gap_map[0], gap_map[2], calc.outputs.array_ndb)
    _cb=find_table_ind(gap_map[1][0], gap_map[1][2], calc.outputs.array_ndb)
    _vb_level_dft = calc.outputs.array_ndb.get_array('Eo')[_vb].real
    _vb_level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real
    _cb_level_dft = calc.outputs.array_ndb.get_array('Eo')[_cb].real
    _cb_level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_cb].real

    _vb_level_gw = (_vb_level_dft + _vb_level_corr)*27.2114
    _cb_level_gw = (_cb_level_dft + _cb_level_corr)*27.2114

    return _cb_level_gw-_vb_level_gw

def additional_parsed(calc, additional_parsing_List, mapping):
    
    parsed_dict = {}
    parsing_List = additional_parsing_List

    val = mapping['valence']
    cond = mapping['conduction']
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']

    for what in parsing_List:
        if isinstance(what,list): 
            key = what[0]
        else:
            key = what

        if key=='gap_' and key in mapping.keys():
    
            homo_gw = parse_qp_level(calc, [homo_k, homo_k, val, val])
            lumo_gw = parse_qp_level(calc, [lumo_k, lumo_k, cond, cond])

            print('homo: ', homo_gw)
            print('lumo: ', lumo_gw)
            print('gap: ', abs(lumo_gw-homo_gw))

            parsed_dict['gap_'] =  abs(lumo_gw-homo_gw)
            parsed_dict['homo'] =  homo_gw
            parsed_dict['lumo'] =  lumo_gw
            continue
        elif key=='homo':

            homo_gw = parse_qp_level(calc, [homo_k, homo_k, val, val])

            parsed_dict['homo'] =  homo_gw

        elif key=='lumo':

            lumo_gw = parse_qp_level(calc, [lumo_k, lumo_k, cond, cond])

            parsed_dict['lumo'] =  lumo_gw
        
        elif 'gap_' in key and key in mapping.keys():

            homo_gw = parse_qp_level(calc, mapping[key][0])
            lumo_gw = parse_qp_level(calc, mapping[key][1])

            print('homo: ', homo_gw)
            print('lumo: ', lumo_gw)
            print('gap: ', abs(lumo_gw-homo_gw))

            parsed_dict[key] =  abs(lumo_gw-homo_gw)
            parsed_dict['homo_'+key[-2]] =  homo_gw
            parsed_dict['lumo_'+key[-1]] =  lumo_gw
        
        
        elif key in mapping.keys():
            if len(mapping[key]) == 2:
                homo_gw = parse_qp_level(calc, mapping[key][0])
                lumo_gw = parse_qp_level(calc, mapping[key][1])
                parsed_dict['homo_'+key+'_v'] =  homo_gw
                parsed_dict['lumo_'+key+'_c'] =  lumo_gw
            else:
                level_gw = parse_qp_level(calc, mapping[key][0])
                parsed_dict[key] =  level_gw
                   
    return parsed_dict