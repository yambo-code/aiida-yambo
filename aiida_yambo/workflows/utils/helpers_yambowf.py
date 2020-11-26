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

    yambo_bandsX = workchain_inputs.yres.yambo.parameters.get_dict().pop('BndsRnXp',[0])[-1]
    yambo_bandsSc = workchain_inputs.yres.yambo.parameters.get_dict().pop('GbndRnge',[0])[-1]
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

    if hasattr(workchain_inputs,'scf_parameters'):
        message_scf = 'scf inputs found'
        messages.append(message_scf)
        scf_params =  workchain_inputs.scf_parameters    
    elif scf_params_parent:
        message_scf = message_scf_parent
        messages.append(message_scf)
        scf_params =  scf_params_parent    
    else:
        message_scf = 'scf inputs not found, setting defaults'
        messages.append(message_scf)
        scf_params = scf_params_def
        scf_params['SYSTEM']['nbnd'] = int(scf_params_def['SYSTEM']['nbnd'])
        scf_params = Dict(dict=scf_params)
    
    redo_nscf = False
    if hasattr(workchain_inputs,'nscf_parameters'):
        message_nscf = 'nscf inputs found' 
        nscf_params =  workchain_inputs.nscf_parameters
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += ', and setting nbnd of the nscf calculation to b = {}'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf)
        
    elif nscf_params_parent:
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
    else:
        message_nscf = 'nscf inputs not found, setting defaults'
        nscf_params = copy.deepcopy(scf_params.get_dict())
        nscf_params['CONTROL']['calculation'] = nscf_params_def['CONTROL']['calculation']
        nscf_params['SYSTEM']['nbnd'] = int(gwbands)
        nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf)
    
            
    if 'defaults' in message_scf:
        message_scf_corr='setting scf defaults according to found nscf'
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
    
    parsing_List = additional_parsing_List.get_list()
    qp_list = []
    #take mapping from nscf
    parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
    nscf = find_pw_parent(parent_calc, calc_type=['nscf'])
    mapping = gap_mapping_from_nscf(nscf.pk,)
    val = mapping['valence']
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']
    
    new_params = workchain_inputs.yambo.parameters.get_dict()
    new_params['QPkrange'] = new_params.pop('QPkrange', [])

    for name in parsing_List:
        if name == 'gap_eV':
            new_params['QPkrange'].append([homo_k, homo_k, val,val])
            new_params['QPkrange'].append([lumo_k,lumo_k, val+1,val+1])
    
        if name == 'homo_level_eV' and not 'gap_eV' in parsing_List:
            new_params['QPkrange'].append([homo_k, homo_k, val,val])
    
        if name == 'lumo_level_eV' and not 'gap_eV' in parsing_List:
            new_params['QPkrange'].append([lumo_k,lumo_k, val+1,val+1])
    
        if name == 'gap_at_Gamma_eV':
            new_params['QPkrange'].append([1, 1, val, val+1])
        
        if len(name.split(','))==2:
            what = name.split(',') 
            quant = what[1].split('_')  #k1_b1_k2_b2
            if len(quant) == 2:
                new_params['QPkrange'].append([int(quant[0]),int(quant[0]),int(quant[1]),int(quant[1])])
            elif len(quant) == 4: #[k1,b1,k2,b2]
                new_params['QPkrange'].append([int(quant[0]),int(quant[0]),int(quant[1]),int(quant[1])])
                new_params['QPkrange'].append([int(quant[2]),int(quant[2]),int(quant[3]),int(quant[3])])
        
        if isinstance(name,tuple) or isinstance(name,list): # ('kpoint_x, band_y', [y,y,x,x]), not working for YamboConvergence
            if len(name[1]) == 2:
                new_params['QPkrange'].append([name[1][0],name[1][0],name[1][1],name[1][1]])
            elif len(name[1]) == 4: #[k1,b1,k2,b2]
                new_params['QPkrange'].append([name[1][0],name[1][0],name[1][1],name[1][1]])
                new_params['QPkrange'].append([name[1][2],name[1][2],name[1][3],name[1][3]])

    return mapping, Dict(dict=new_params)

def parse_qp_level(calc, band, k):

    _vb=find_table_ind(band, k, calc.outputs.array_ndb)
    level_dft = calc.outputs.array_ndb.get_array('Eo')[_vb].real
    level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real

    level_gw = (level_dft + level_corr)*27.2114

    return level_gw

def additional_parsed(calc, additional_parsing_List, mapping):
    
    parsed_dict = {}
    parsing_List = additional_parsing_List.get_list()

    val = mapping['valence']
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']

    for what in parsing_List:
        if what=='gap_eV':
    
            homo_gw = parse_qp_level(calc, val, homo_k)
            lumo_gw = parse_qp_level(calc, val+1, lumo_k)

            print('homo: ', homo_gw)
            print('lumo: ', lumo_gw)
            print('gap: ', abs(lumo_gw-homo_gw))

            parsed_dict['gap_eV'] =  abs(lumo_gw-homo_gw)
            parsed_dict['homo_level_eV'] =  homo_gw
            parsed_dict['lumo_level_eV'] =  lumo_gw

        if what=='homo_level_eV':

            homo_gw = parse_qp_level(calc, val, homo_k)

            parsed_dict['homo_level_eV'] =  homo_gw

        if what=='lumo_level_eV':

            lumo_gw = parse_qp_level(calc, val+1, lumo_k)

            parsed_dict['lumo_level_eV'] =  lumo_gw
        
        if what=='gap_at_Gamma_eV':

            homo_gw = parse_qp_level(calc, val, 1)
            lumo_gw = parse_qp_level(calc, val+1, 1)

            print('homo: ', homo_gw)
            print('lumo: ', lumo_gw)
            print('gap: ', abs(lumo_gw-homo_gw))

            parsed_dict['gap_at_Gamma_eV'] =  abs(lumo_gw-homo_gw)
            parsed_dict['homo_level_at_Gamma_eV'] =  homo_gw
            parsed_dict['lumo_level_at_Gamma_eV'] =  lumo_gw
        
        if len(what.split(','))==2:
            whats = what.split(',') 
            quant = whats[1].split('_')  #k1_b1_k2_b2
            if len(quant) == 2:
                level = parse_qp_level(calc, int(quant[1]), int(quant[0]))
                parsed_dict[what] =  level
            elif len(quant) == 4: #[k1,b1,k2,b2]
                level_1 = parse_qp_level(calc, int(quant[1]), int(quant[0]))
                level_2 = parse_qp_level(calc, int(quant[3]), int(quant[2]))
                level_diff = abs(level_2-level_1)
                parsed_dict[what] =  level_diff

        if isinstance(what,tuple) or isinstance(what,list):
            if len(what[1])==2:
                level = parse_qp_level(calc, what[1][1], what[1][0])
                parsed_dict[what[0]] =  level

            elif len(what[1])==4:
                level_1 = parse_qp_level(calc, what[1][1], what[1][0])
                level_2 = parse_qp_level(calc, what[1][3], what[1][2])
                level_diff = abs(level_2-level_1)
                parsed_dict[what[0]] =  level_diff
            
    return parsed_dict