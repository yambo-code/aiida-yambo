# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import cmath

from yambopy.dbs.qpdb import *
from yambopy.dbs.savedb import * 
from qepy.lattice import Path
from aiida.tools.data.array.kpoints import get_kpoints_path, get_explicit_kpoints_path

try:
    from aiida.orm import Dict, Str, load_node, KpointsData, Bool, StructureData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
    from aiida_yambo.utils.parallelism_finder import *
except:
    pass

from aiida_yambo.utils.defaults.create_defaults import *

def QP_bands(node,mapping=None,only_scissor=False, plot=False):
    
    x = node

    save_dir = x.outputs.output_parameters.get_dict()['ns_db1_path']
    qp_dir = x.outputs.retrieved._repository._repo_folder.abspath+'/path'
    
    lat  = YamboSaveDB.from_db_file(folder=save_dir,filename='ns.db1')  
    ydb  = YamboQPDB.from_db(filename='ndb.QP',folder=qp_dir)
        
    if mapping: 
        valence = mapping.get_dict()['valence']
        kpoints=  mapping.get_dict()['number_of_kpoints']
    else:
        valence = x.outputs.nscf_mapping.get_dict()['valence']
        kpoints= x.outputs.nscf_mapping.get_dict()['number_of_kpoints']

    scissor = ydb.get_scissor(valence=valence)
    
    if only_scissor: return scissor,0,0,0

    if plot:
         ydb.plot_scissor(valence=valence)
    
    pw = find_pw_parent(x,)
    try:
        k_params = get_kpoints_path(pw.inputs.structure)['parameters'].get_dict()
        bulk = True
    except:
        bulk = False
        fake_bulk = StructureData(ase=pw.inputs.structure.get_ase())
        fake_bulk.set_pbc([True,True,True])
        k_params = get_kpoints_path(fake_bulk)['parameters'].get_dict()
        
    p = []
    exit = False
    for line in k_params['path']:
        if exit: break
        for point in line:
            if point == 'GAMMA' or point == 'G':
                print(point)
                print(p)
                print(len(p),bulk)
                if len(p) > 0 and bulk:
                    if '$\Gamma$' == p[-1][-1]:
                        print('continue')
                        continue
                elif len(p) > 1 and not bulk:
                    print('uscire')
                    exit = True
                    p.append([k_params['point_coords'][point],'$\Gamma$'])
                    break
                else:
                    p.append([k_params['point_coords'][point],'$\Gamma$'])

            else:
                print(point)
                if point == p[-1][-1]:
                    continue
                p.append([k_params['point_coords'][point],point])                
                for i in range(3):
                    if not pbc[i]:
                        if abs(k_params['point_coords'][point][i]) > 0:
                            p.pop(-1)              
    
    path_full = Path(p, [int(kpoints*2)]*(len(p)-1) )
    
    ks_bs_0, qp_bs_0 = ydb.get_bs_path(lat, path_full)
    ks_bs_1, qp_bs_1 = ydb.interpolate(lat, path_full)
    
    lab = [(0,'GAMMA')]

    space = qp_bs_1.kpath.as_dict()['intervals'][0]
    ind = space
    for i in qp_bs_1.kpath.as_dict()['klabels'][1:]:
        if i == lab[-1][1]:
            lab.append((ind-space,i))
        else:
            lab.append((ind,i))
        ind += space
    
    return scissor, ks_bs_1, qp_bs_1, lab

@calcfunction
def QP_bands_interface(node, mapping, only_scissor=Bool(False)):
    
    x = load_node(node.value)
    
    scissor, ks_bs_1, qp_bs_1, lab = QP_bands(x,mapping,only_scissor= only_scissor)

    if only_scissor: return {'scissor':List(list=[scissor[0],scissor[1],scissor[2]])}
        
    BandsData = DataFactory('array.bands')
    gw_bands_data = BandsData()
    
    gw_bands_data.set_kpoints(qp_bs_1.kpoints)
    gw_bands_data.set_bands(qp_bs_1.bands, units='eV')
    gw_bands_data.labels = lab
    
    dft_bands_data = BandsData()
    
    dft_bands_data.set_kpoints(ks_bs_1.kpoints)
    dft_bands_data.set_bands(ks_bs_1.bands, units='eV')
    dft_bands_data.labels = lab

    #bands_data.show_mpl() # to visualize the bands
    print([scissor[0],scissor[1],scissor[2]])
    return {'band_structure_DFT':dft_bands_data, 
            'band_structure_GW':gw_bands_data, 
            'scissor':List(list=[scissor[0],scissor[1],scissor[2]])}


def quantumespresso_input_validator(workchain_inputs,overrides={'pw':{}}):
    
    messages = []

    yambo_bandsX = workchain_inputs.yres.yambo.parameters.get_dict()['variables'].pop('BndsRnXp',[[0],''])[0][-1]
    yambo_bandsSc = workchain_inputs.yres.yambo.parameters.get_dict()['variables'].pop('GbndRnge',[[0],''])[0][-1]
    gwbands = max(yambo_bandsX,yambo_bandsSc)
    message_bands = 'GW bands are: {}'.format(gwbands)
    messages.append(message_bands)
    scf_params, nscf_params = None, None
    #scf_params_def, nscf_params_def = create_quantumespresso_inputs(structure, bands_gw = gwbands)

    if hasattr(workchain_inputs,'parent_folder'):
        try:
            parent_calc = workchain_inputs.parent_folder.creator #take_calc_from_remote(workchain_inputs.parent_folder)
        except:
            parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
           
        try:
            scf_params_parent = find_pw_parent(parent_calc, calc_type=['scf']).inputs.parameters
            message_scf_parent = 'found scf inputs from parent'
        except:
            scf_params_parent = False
    else:
        scf_params_parent = False

    if hasattr(workchain_inputs,'parent_folder'):
        try:
            parent_calc = workchain_inputs.parent_folder.creator #take_calc_from_remote(workchain_inputs.parent_folder)
        except:
            parent_calc = take_calc_from_remote(workchain_inputs.parent_folder)
        try:
            nscf_params_parent = find_pw_parent(parent_calc, calc_type=['nscf']).inputs.parameters
            message_nscf_parent = 'found nscf inputs from parent\n'
        except:
            nscf_params_parent = False
    else:
        nscf_params_parent = False

    if scf_params_parent:
        message_scf = message_scf_parent
        messages.append(message_scf)
        scf_params =  scf_params_parent 
    elif hasattr(workchain_inputs.scf.pw,'parameters'):
        message_scf = 'scf inputs found'
        messages.append(message_scf)
        scf_params =  workchain_inputs.scf.pw.parameters
    else:
        message_scf = 'scf inputs not found, setting defaults'
        messages.append(message_scf)
        scf_params = None
    #else:
    #    message_scf = 'scf inputs not found, setting defaults'
    #    messages.append(message_scf)
    #    scf_params = scf_params_def
    #    scf_params['SYSTEM']['nbnd'] = int(scf_params_def['SYSTEM']['nbnd'])
    #    scf_params = Dict(dict=scf_params)
    
    redo_nscf = False
        
    if nscf_params_parent:
        message_nscf = message_nscf_parent
        messages.append(message_nscf)
        nscf_params =  nscf_params_parent
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += ' and setting nbnd of the nscf calculation to b = {}'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
            messages.append(message_nscf)  
    elif hasattr(workchain_inputs.nscf.pw,'parameters'):
        message_nscf = 'nscf inputs found' 
        nscf_params =  workchain_inputs.nscf.pw.parameters
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += ', and setting nbnd of the nscf calculation to b = {}\n'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
        messages.append(message_nscf)  
    elif hasattr(workchain_inputs.nscf.pw,'parameters'):
        message_nscf = 'nscf inputs found\n' 
        nscf_params =  workchain_inputs.nscf.pw.parameters
        if nscf_params.get_dict()['SYSTEM']['nbnd'] < gwbands:
            redo_nscf = True
            message_nscf += ', and setting nbnd of the nscf calculation to b = {}\n'.format(gwbands)
            nscf_params = nscf_params.get_dict()
            nscf_params['SYSTEM']['nbnd'] = int(gwbands)
            nscf_params = Dict(dict=nscf_params)
        else:
            nscf_params = None
        messages.append(message_nscf)       
    #else:
    #    message_nscf = 'nscf inputs not found, setting defaults'
    #    nscf_params = copy.deepcopy(scf_params.get_dict())
    #    nscf_params['CONTROL']['calculation'] = nscf_params_def['CONTROL']['calculation']
    #    nscf_params['SYSTEM']['nbnd'] = int(gwbands)
    #    nscf_params = Dict(dict=nscf_params)
    #    messages.append(message_nscf)
    
            
    '''if 'defaults' in message_scf:
        message_scf_corr='setting scf defaults according to nscf'
        messages.append(message_scf_corr)
        scf_params = copy.deepcopy(scf_params.get_dict())
        bands_scf = scf_params['SYSTEM']['nbnd']
        scf_params['SYSTEM'] = copy.deepcopy(nscf_params['SYSTEM'])
        scf_params['CONTROL']['calculation'] = 'scf'
        scf_params['SYSTEM']['nbnd'] = int(bands_scf)
        scf_params = Dict(dict=scf_params)'''
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

def add_corrections(workchain_inputs, additional_parsing_List): #pre proc
    
    parsing_List = additional_parsing_List
    qp_list = []
    #take mapping from nscf
    parent_calc = take_calc_from_remote(workchain_inputs.parent_folder,level=-1)
    try:
        nscf = find_pw_parent(parent_calc, calc_type=['nscf'])
    except:
        nscf = parent_calc
    mapping = gap_mapping_from_nscf(nscf.pk, additional_parsing_List)
    val = mapping['valence']
    cond = mapping['conduction'] 
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']
    number_of_kpoints = mapping['number_of_kpoints']
    sub_val = 3 
    sup_cond = 3 #so, for now 3+3 bands

    new_params = copy.deepcopy(workchain_inputs.yambo.parameters.get_dict())
    
    QP = []
    for i in new_params['variables']['QPkrange'][0]:
        if i[0] > number_of_kpoints or i[1] > number_of_kpoints:
            pass
        else:
            QP.append(i)
    try:
        QP = [QP[0]]
    except:
        QP = []
    for name in parsing_List:

        if 'exciton' in parsing_List:
            pass
        elif isinstance(name,list) and name[0] in mapping.keys():
            for i in mapping[name[0]]:
                if not i in QP: QP.append(i) 
        elif isinstance(name,str) and name in mapping.keys():
            for i in mapping[name]:
                if not i in QP: QP.append(i) 
    
        elif name == 'homo':
           if not [homo_k, homo_k, val,val] in QP: QP.append([homo_k, homo_k, val,val])
    
        elif name == 'lumo':
            if not [lumo_k,lumo_k, cond,cond] in QP: QP.append([lumo_k,lumo_k, cond,cond])
        
        elif name == 'band_structure':
            #if 'QPkrange' in new_params['variables'].keys() and new_params['variables']['QPkrange'][0][3]-new_params['variables']['QPkrange'][0][2]>0:
            #    new_params['variables']['QPkrange'][0] = [1,number_of_kpoints, new_params['variables']['QPkrange'][0][2],new_params['variables']['QPkrange'][0][3]]
            #else:
                QP = [1,number_of_kpoints, val-sub_val,cond+sup_cond]
                break
        
        elif 'band_structure' in name:    #should provide as 'band_structure_vN_cM', where N, M are the amount of valence and conduction bands included 
            #if 'QPkrange' in new_params['variables'].keys() and new_params['variables']['QPkrange'][0][3]-new_params['variables']['QPkrange'][0][2]>0:
            #    new_params['variables']['QPkrange'][0] = [1,number_of_kpoints, new_params['variables']['QPkrange'][0][2],new_params['variables']['QPkrange'][0][3]]
            #else:
                QP = [1,number_of_kpoints, val-int(name[-4])+1,cond+int(name[-1])-1]
                break
    

    new_params['variables']['QPkrange']= [QP,'']

    return mapping, Dict(dict=new_params)

def parse_qp_level(calc, level_map):

    _vb=find_table_ind(level_map[2], level_map[1], calc.outputs.array_ndb)
    level_dft = calc.outputs.array_ndb.get_array('Eo')[_vb].real
    level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real

    level_gw = (level_dft + level_corr)*27.2114

    return level_gw, level_dft*27.2114

def parse_qp_gap(calc, gap_map): #post proc 

    _vb=find_table_ind(gap_map[0], gap_map[2], calc.outputs.array_ndb)
    _cb=find_table_ind(gap_map[1][0], gap_map[1][2], calc.outputs.array_ndb)
    _vb_level_dft = calc.outputs.array_ndb.get_array('Eo')[_vb].real
    _vb_level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_vb].real
    _cb_level_dft = calc.outputs.array_ndb.get_array('Eo')[_cb].real
    _cb_level_corr = calc.outputs.array_ndb.get_array('E_minus_Eo')[_cb].real

    _vb_level_gw = (_vb_level_dft + _vb_level_corr)*27.2114
    _cb_level_gw = (_cb_level_dft + _cb_level_corr)*27.2114



    return _cb_level_gw-_vb_level_gw, _cb_level_dft*27.2114-_vb_level_dft*27.2114

def parse_excitons(calc, what): #post proc 

    if what == 'brightest':
        index = calc.outputs.array_excitonic_states.get_array('intensities').argmax()
        brightest = calc.outputs.array_excitonic_states.get_array('energies')[index]
        return brightest, index+1
    elif what == 'lowest':
        lowest = calc.outputs.array_excitonic_states.get_array('energies')[0]
        return lowest, 1 

def additional_parsed(calc, additional_parsing_List, mapping): #post proc 
    
    parsed_dict = {}
    parsing_List = additional_parsing_List

    val = mapping['valence']
    cond = mapping['conduction']
    homo_k = mapping['homo_k']
    lumo_k = mapping['lumo_k']

    for what in parsing_List:
        try:
            if isinstance(what,list): 
                key = what[0]
            else:
                key = what

            if key=='gap_' and key in mapping.keys():
        
                homo_gw, homo_dft = parse_qp_level(calc, [homo_k, homo_k, val, val])
                lumo_gw, lumo_dft = parse_qp_level(calc, [lumo_k, lumo_k, cond, cond])

                print('homo: ', homo_gw)
                print('lumo: ', lumo_gw)
                print('gap: ', lumo_gw-homo_gw)

                parsed_dict['gap_'] =  lumo_gw-homo_gw
                parsed_dict['homo'] =  homo_gw
                parsed_dict['lumo'] =  lumo_gw

                parsed_dict['gap_dft'] =  lumo_dft-homo_dft
                parsed_dict['homo_dft'] =  homo_dft
                parsed_dict['lumo_dft'] =  lumo_dft
                continue
            
            elif key=='homo':

                homo_gw, homo_dft = parse_qp_level(calc, [homo_k, homo_k, val, val])

                parsed_dict['homo'] =  homo_gw
                parsed_dict['homo_dft'] =  homo_dft

            elif key=='lumo':

                lumo_gw, lumo_dft = parse_qp_level(calc, [lumo_k, lumo_k, cond, cond])

                parsed_dict['lumo'] =  lumo_gw
                parsed_dict['lumo_dft'] =  lumo_dft
            
            elif 'gap_' in key and key in mapping.keys():

                homo_gw, homo_dft = parse_qp_level(calc, mapping[key][0])
                lumo_gw, lumo_dft = parse_qp_level(calc, mapping[key][1])

                print('homo: ', homo_gw)
                print('lumo: ', lumo_gw)
                print('gap: ', lumo_gw-homo_gw)

                parsed_dict[key] =  lumo_gw-homo_gw
                parsed_dict['homo_'+key[-2]] =  homo_gw
                parsed_dict['lumo_'+key[-1]] =  lumo_gw

                parsed_dict[key+'_dft'] =  lumo_dft-homo_dft
                parsed_dict['homo_'+key[-2]+'_dft'] =  homo_dft
                parsed_dict['lumo_'+key[-1]+'_dft'] =  lumo_dft
            
            elif key=='brightest_exciton':

                exciton, index = parse_excitons(calc, 'brightest')

                parsed_dict['brightest_exciton'] =  exciton
                parsed_dict['brightest_exciton_index'] =  index
            
            elif key=='lowest_exciton':

                exciton, index = parse_excitons(calc, 'lowest')

                parsed_dict['lowest_exciton'] =  exciton
                parsed_dict['lowest_exciton_index'] =  index
            
            
            elif key in mapping.keys():
                
                    if len(mapping[key]) == 2:
                        homo_gw, homo_dft = parse_qp_level(calc, mapping[key][0])
                        lumo_gw, lumo_dft = parse_qp_level(calc, mapping[key][1])
                        parsed_dict['homo_'+key+'_v'] =  homo_gw
                        parsed_dict['lumo_'+key+'_c'] =  lumo_gw

                        parsed_dict['homo_'+key+'_v_dft'] =  homo_dft
                        parsed_dict['lumo_'+key+'_c_dft'] =  lumo_dft
                    else:
                        level_gw, level_dft = parse_qp_level(calc, mapping[key][0])
                        parsed_dict[key] =  level_gw
                        parsed_dict[key+'_dft'] =  level_dft
            
        except:
            parsed_dict[key] =  False

    return parsed_dict


def organize_output(output, node=None): #prepare to be stored
    
    if isinstance(output,dict):
        for k in output.keys():
            if 'band_structure' in k and node:
                pass
            else:
                return Dict(dict=output)
                break
    
    elif isinstance(output,list):
        return List(list=output)

