# -*- coding: utf-8 -*-
"""helpers for many purposes"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import os

try:
    from aiida.orm import Dict, Str, List, load_node, KpointsData, RemoteData, Group
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida.engine import calcfunction 
except:
    pass

from aiida_yambo.utils.k_path_utils import * 

def find_parent(calc):

    try:
        parent_calc = calc.inputs.parent_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
    except:
        try:
            parent_calc = calc.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
        except:
            parent_calc = calc.called[0] #nscf_workchain...??
    return parent_calc

def find_pw_parent(parent_calc, calc_type = ['scf', 'nscf']):

    has_found_pw = False
    while (not has_found_pw):
        if parent_calc.process_type=='aiida.calculations:yambo.yambo' or parent_calc.process_type=='aiida.workflows:yambo.yambo.yambowf':
            has_found_pw = False
            parent_calc = find_parent(parent_calc)
            if parent_calc.process_type=='aiida.workflows:quantumespresso.pw.base':
                parent_calc = parent_calc.called[0]
            if parent_calc.process_type=='aiida.calculations:quantumespresso.pw' and \
                find_pw_type(parent_calc) in calc_type:
                has_found_pw = True
            else:
                parent_calc = find_parent(parent_calc)
        elif parent_calc.process_type=='aiida.calculations:quantumespresso.pw' and \
            find_pw_type(parent_calc) in calc_type:
            has_found_pw = True
        else:
            parent_calc = find_parent(parent_calc)

    return parent_calc

def get_distance_from_kmesh(calc):
    mesh = calc.inputs.kpoints.get_kpoints_mesh()[0]
    k = KpointsData()
    k.set_cell_from_structure(calc.inputs.structure) #these take trace of PBC...if set in the inputs.!!
    for i in range(4,400):
         k.set_kpoints_mesh_from_density(1/(i*0.25))
         if k.get_kpoints_mesh()[0]==mesh:
             print('ok, {} is the density'.format(i*0.25))
             print(k.get_kpoints_mesh()[0],mesh)
             return i*0.25

def find_pw_type(calc):
    type = calc.inputs.parameters.get_dict()['CONTROL']['calculation']
    return type

def find_table_ind(kpoint,band,_array_ndb):
    kk = _array_ndb.get_array('qp_table')
    b = kk[-1]==band
    c = kk[0]==kpoint
    g = (c == True) & (b == True)
    for i in range(len(g)):
        if g[i] == True:
            return(i)


def update_dict(_dict, whats, hows, sublevel=None):
    if sublevel:
        if not isinstance(whats, list):
            whats = [whats]
        if not isinstance(hows, list):
            hows = [hows] 
        for what,how in zip(whats,hows):    
            new = _dict.get_dict()
            new[sublevel][what] = how
            _dict = Dict(dict=new)
    else:
        if not isinstance(whats, list):
            whats = [whats]
        if not isinstance(hows, list):
            hows = [hows] 
        for what,how in zip(whats,hows):    
            new = _dict.get_dict()
            new[what] = how
            _dict = Dict(dict=new)
    return _dict

def get_caller(calc_pk, depth = 1):
     calc = load_node(calc_pk)
     for i in range(depth):
         calc = calc.caller.caller
     return calc

def get_called(calc_pk, depth = 2):
     calc = load_node(calc_pk)
     for i in range(depth):
         calc = calc.called[0]
     return calc

def set_parent(inputs, parent):
     if isinstance(parent, RemoteData):
         inputs.parent_folder = parent
     else:
         inputs.parent_folder = parent.outputs.remote_folder

def take_down(node = 0, what = 'CalcJobNode'):

     global calc_node

     if node == 0:
         node = load_node(wfl_pk)
     else:
         node = load_node(node)

     if what not in str(node.get_description):
         take_down(node.called[0])
     else:
         calc_node = node

     return calc_node

def take_super(node = 0, what = 'WorkChainNode'):

     global workchain_node

     if node == 0:
         node = load_node(wfl_pk)
     else:
         node = load_node(node)

     if what not in str(node.get_description):
         take_super(node.caller)
     else:
         workchain_node = node

     return workchain_node

def take_calc_from_remote(parent_folder):
        try:
            parent_calc = parent_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
        except:
            parent_calc = parent_folder.get_incoming().get_node_by_label('remote_folder')
        return parent_calc

def take_fermi(calc_node_pk):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    node = load_node(calc_node_pk)
    path_folder = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
    for i in os.listdir(path_folder):
        if 'r-aiida.out' in i:
            file = open(path_folder+i,'r')
    for line in file:
        if '[X]Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[3]))
            ef = float(line.split()[3])

    return ef

def take_filled_states(calc_node_pk):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    node = load_node(calc_node_pk)
    path_folder = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
    get_line=False #not so good...
    for i in os.listdir(path_folder):
        if 'r-aiida.out' in i:
            file = open(path_folder+i,'r')
    for line in file:
        if  get_line:
            print('The VBM {}'.format(line.split()[0]))
            valence = int(line.split()[0].replace('0001-',''))
            return valence
        if '[X]States summary ' in line:
            get_line=True

    

def take_number_kpts(calc_node_pk):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    node = load_node(calc_node_pk)
    path_folder = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
    for i in os.listdir(path_folder):
        if 'r-aiida.out' in i:
            file = open(path_folder+i,'r')
    for line in file:
        if 'K-points' in line:
            print('# of kpts is {}'.format(line.split()[2]))
            kpts = int(line.split()[2])
            return kpts
    
def store_List(a_list):
    the_List = List(list=a_list)
    the_List.store()
    return the_List

def store_Dict(a_dict):
    the_Dict = Dict(dict=a_dict)
    the_Dict.store()
    return the_Dict

def find_pw_info(calc):

    pw_parent = find_pw_parent(calc, calc_type = ['nscf'])
    info = pw_parent.outputs.output_parameters.get_dict()   
    return info

def find_gw_info(inputs):

    parameters = copy.deepcopy(inputs.parameters.get_dict())
    
    ## bands ##

    BndsRnXp = parameters['variables'].pop('BndsRnXp',[[0],''])[0]
    GbndRnge = parameters['variables'].pop('GbndRnge',[[0],''])[0]
    X_b = 1 + BndsRnXp[1] - BndsRnXp[0]
    SE_b = 1 + GbndRnge[1] - GbndRnge[0]
    if X_b and SE_b:
        bands = min(X_b,SE_b)
    elif X_b and not SE_b:
        bands = X_b
    elif not X_b and SE_b:
        bands = SE_b
    else: bands = 1

    ## parallelism ##

    ## qp ##

    qp = 0
    last_qp = 0
    for i in parameters['variables']['QPkrange'][0]:
        qp += (1 + i[1]-i[0])*(1 + i[3]-i[2])
        last_qp = max(i[3],last_qp)

    ## runlevels ##
    runlevels = []
    for i in parameters['arguments']:
        runlevels.append(i)
    
    return bands, qp, last_qp, runlevels

def build_list_QPkrange(mapping, quantity, nscf_pk):
    s = load_node(nscf_pk)
    if isinstance(quantity,str):
        if 'gap_' in quantity:
            if quantity[-1] == '_': 
                pass
            else: #high-symmetry
                m,maps = k_path_dealer().check_kpoints_in_qe_grid(s.outputs.output_band.get_kpoints(),
                                       s.inputs.structure.get_ase())
                
                if quantity[-1] in m or quantity[-2] in m: return quantity, 0
                if not quantity[-1] in maps.keys() or not quantity[-2] in maps.keys(): return quantity, 0
                return quantity,[[maps[quantity[-2]],maps[quantity[-2]],
                         mapping['valence'],mapping['valence']],
                        [maps[quantity[-1]],maps[quantity[-1]],
                         mapping['conduction'],mapping['conduction']]]
        else: #high-symmetry
                m,maps = k_path_dealer().check_kpoints_in_qe_grid(s.outputs.output_band.get_kpoints(),
                                       s.inputs.structure.get_ase())
                
                if quantity in m : return quantity, 0
                if not quantity in maps.keys(): return quantity, 0
                if '_v' in quantity:
                    return quantity,[[maps[quantity[0]],maps[quantity[0]],
                         mapping['valence'],mapping['valence']],]
                elif '_c' in quantity:
                    return quantity,[[maps[quantity[0]],maps[quantity[0]],
                         mapping['conduction'],mapping['conduction']],]
                
                return quantity,[[maps[quantity],maps[quantity],
                         mapping['valence'],mapping['valence']],
                        [maps[quantity],maps[quantity],
                         mapping['conduction'],mapping['conduction']]]
            
    elif isinstance(quantity,list):
        if 'gap_' in quantity[0]:
            m,maps = k_path_dealer().check_kpoints_in_qe_grid(s.outputs.output_band.get_kpoints(),
                                       s.inputs.structure.get_ase(),k_list={quantity[0][-2]:np.array(quantity[1][-2]),
                                                                            quantity[0][-1]:np.array(quantity[1][-1])})

            if quantity[0] in m : return quantity[0], 0    
            return quantity[0],[[maps[quantity[0][-2]],maps[quantity[0][-2]],
                     mapping['valence'],mapping['valence']],
                    [maps[quantity[0][-1]],maps[quantity[0][-1]],
                     mapping['conduction'],mapping['conduction']]]
        else:
            m,maps = k_path_dealer().check_kpoints_in_qe_grid(s.outputs.output_band.get_kpoints(),
                                       s.inputs.structure.get_ase(),k_list={quantity[0]:np.array(quantity[1]),
                                                                            quantity[0]:np.array(quantity[1])})
            
            if quantity[0] in m : return quantity[0], 0
            if '_v' in quantity[0]:
                return quantity[0],[[maps[quantity[0]],maps[quantity[0]],
                     mapping['valence'],mapping['valence']],]
            elif '_c' in quantity[0]:
                return quantity[0],[[maps[quantity[0]],maps[quantity[0]],
                     mapping['conduction'],mapping['conduction']],]
            
            
            return quantity[0],[[maps[quantity[0]],maps[quantity[0]],
                     mapping['valence'],mapping['valence']],
                    [maps[quantity[0]],maps[quantity[0]],
                     mapping['conduction'],mapping['conduction']]]     
    else:
        return 0, 0
def gap_mapping_from_nscf(nscf_pk, additional_parsing_List=[]):
    
    nscf = load_node(nscf_pk)
    bands = nscf.outputs.output_band.get_array('bands')
    occ = nscf.outputs.output_band.get_array('occupations')
    n_kpoints = nscf.outputs.output_parameters.get_dict()['number_of_k_points']
    k_coords = nscf.outputs.output_band.get_kpoints()
    valence = len(occ[0][occ[0]>0.01]) #band index of the valence. 
    valence = nscf.outputs.output_parameters.get_dict()['number_of_electrons']/2.
    fermi = nscf.outputs.output_parameters.get_dict()['fermi_energy']
    soc = nscf.outputs.output_parameters.get_dict()['spin_orbit_calculation']
    
    try:
        try:
            nscf.inputs.pw__structure.get.ase()
        except:
            nscf.inputs.structure.get.ase()
        cell = structure.get_cell()
        k = cell.bandpath()
        high_symmetry = k.special_points
    except:
        high_symmetry = []
    if valence%2 != 0:
        valence = int(valence+0.5) #may be a metal
    else:
        valence = int(valence)
    conduction = valence + 1  
    
    if soc:
        valence = valence*2 - 1
        conduction = valence + 2

    touch_fermi = np.where(abs(bands[:,valence-1]-fermi)<0.005)
    if len(touch_fermi)>1: #metal??
        ind_val = touch_fermi[0]
        ind_cond = ind_val
        dft_predicted = 'metal'
    else:
        if abs(bands[:,valence-1].argmax() - bands[:,conduction-1].argmin()) > 0.005: #semiconductor, insulator??
            ind_val = bands[:,valence-1].argmax()
            ind_cond = bands[:,conduction-1].argmin()
            dft_predicted = 'semiconductor/insulator'
        else: #semimetal??
            ind_val = bands[:,valence-1].argmax()
            ind_cond = bands[:,conduction-1].argmin()
            dft_predicted = 'semimetal'

    if ind_val+1 != ind_cond+1:
        gap_type = 'indirect'
    else:
        gap_type = 'direct'

    mapping = {
    'dft_predicted': dft_predicted,
    'valence': valence,
    'conduction': conduction,
    'number_of_kpoints':n_kpoints,
    'nscf_gap_eV':round(abs(min(bands[:,conduction-1])-max(bands[:,valence-1])),3),
    'homo_k': ind_val+1,
    'lumo_k': ind_cond+1,
    'gap_type': gap_type,
    'gap_': [[ind_val+1,ind_val+1,valence,valence],
            [ind_cond+1,ind_cond+1,conduction,conduction]], #the qp to be computed
    'soc':soc,
           }

    for i in additional_parsing_List + high_symmetry:
        if i == 'homo' or i == 'lumo' or i == 'gap_':
            pass
        else:
            name, additional = build_list_QPkrange(mapping, i, nscf_pk)
            if additional == 0: 
                pass
            else:
                mapping[name] = additional

    return mapping

def check_identical_calculation(YamboWorkflow_inputs, 
                                YamboWorkflow_list,
                                what=['BndsRnXp','GbndRnge','NGsBlkXp',],
                                full = True,
                                exclude = ['CPU','ROLEs','QPkrange']):

    already_done = False
    parent_nscf = False
    try:
        k_mesh_to_calc = YamboWorkflow_inputs.nscf.kpoints.get_kpoints_mesh()
        params_to_calc = YamboWorkflow_inputs.yres.yambo.parameters.get_dict()
    except:
        k_mesh_to_calc = YamboWorkflow_inputs.nscf__kpoints.get_kpoints_mesh()
        params_to_calc = YamboWorkflow_inputs.yres__yambo__parameters.get_dict()        
    for k in ['kpoint_mesh','k_mesh_density']:
        try:
            what.remove(k)
        except:
            pass
        
    if full: 
        what = copy.deepcopy(list(params_to_calc.keys()))
        what_2 = copy.deepcopy(what)
        #print(what)
        for e in exclude:
            #print(e)
            for p in what_2:
                if e in p: 
                    what.remove(p)
                    #print(p)
        #print(what)            
    
    for old in YamboWorkflow_list:
        try:
            if load_node(old).is_finished_ok:
                same_k = k_mesh_to_calc == load_node(old).inputs.nscf__kpoints.get_kpoints_mesh()
                old_params = load_node(old).inputs.yres__yambo__parameters.get_dict()
                for p in what:
                    #print(p,params_to_calc[p],old_params[p])
                    if params_to_calc[p] == old_params[p] and same_k:
                        already_done = old
                    else:
                        already_done = False
                        break

            if already_done: break
        except:
            already_done = False
    
    for old in YamboWorkflow_list:
        try:
            if  not already_done and not load_node(old).is_finished_ok:
                print(old)
                parent_nscf_try = find_pw_parent(load_node(old).called[0], calc_type=['nscf'])
                same_k = k_mesh_to_calc == load_node(old).inputs.nscf__kpoints.get_kpoints_mesh()
                try:
                    y = load_node(old).outputs.retrieved._repository._repo_folder.abspath+'/path/'
                    if 'ns.db1' in  os.listdir(y) and same_k:
                        parent_nscf = old
                        
                except:
                    pass
                if parent_nscf: break
                if same_k and parent_nscf_try.is_finished_ok: 
                    parent_nscf = parent_nscf_try.pk
            if parent_nscf: break       
        except:
            parent_nscf = False

    return already_done, parent_nscf 

def check_same_yambo(node, params_to_calc, k_mesh_to_calc,what,up_to_p2y=False):
    already_done = False
    try:
        if node.is_finished_ok:
            same_k = k_mesh_to_calc == node.inputs.nscf__kpoints.get_kpoints_mesh()
            old_params = node.inputs.yres__yambo__parameters.get_dict()
            for p in what:
                print(p,params_to_calc[p],old_params[p])
                if up_to_p2y and same_k:
                    already_done = node.pk
                    break
                elif params_to_calc['variables'][p][0] == old_params['variables'][p][0] and same_k:
                    already_done = node.pk
                else:
                    already_done = False
                    break 
    
    except:
        pass
    
    return already_done

def check_same_pw(node, k_mesh_to_calc, already_done):
    parent_nscf = False
    parent_scf = False
    try:
        if not already_done:
            
            parent_nscf_try = find_pw_parent(node, calc_type=['nscf'])
            same_k = k_mesh_to_calc == node.inputs.nscf__kpoints.get_kpoints_mesh()
            if node.is_finished_ok:
                try:
                    y = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
                    if 'ns.db1' in  os.listdir(y) and same_k:
                        parent_nscf = node.pk                    
                except:
                    pass
            if same_k and parent_nscf_try.is_finished_ok: 
                parent_nscf = parent_nscf_try.pk     
            if parent_scf_try.is_finished_ok: 
                parent_scf = parent_scf_try.pk 
   
    except:
        pass
    
    return parent_nscf, parent_scf   

def search_in_group(YamboWorkflow_inputs, 
                                YamboWorkflow_group,
                                what=['BndsRnXp','GbndRnge','NGsBlkXp',],
                                full = True,
                                exclude = ['CPU','ROLEs','QPkrange'],
                                up_to_p2y = False):

    already_done = False
    parent_nscf = False
    try:
        k_mesh_to_calc = YamboWorkflow_inputs.nscf.kpoints.get_kpoints_mesh()
        params_to_calc = YamboWorkflow_inputs.yres.yambo.parameters.get_dict()
    except:
        k_mesh_to_calc = YamboWorkflow_inputs.nscf__kpoints.get_kpoints_mesh()
        params_to_calc = YamboWorkflow_inputs.yres__yambo__parameters.get_dict()        
    for k in ['kpoint_mesh','k_mesh_density']:
        try:
            what.remove(k)
        except:
            pass
        
    if full: 
        what = copy.deepcopy(list(params_to_calc.keys()))
        what_2 = copy.deepcopy(what)
        for e in exclude:
            for p in what_2:
                if e in p: 
                    what.remove(p)     
    
    for old in YamboWorkflow_group.nodes:
        if old.process_type == 'aiida.workflows:yambo.yambo.yamboconvergence':
            for i in old.called:
                already_done = check_same_yambo(i, params_to_calc,k_mesh_to_calc,what,up_to_p2y=up_to_p2y)
                if already_done: break

        elif old.process_type == 'aiida.workflows:yambo.yambo.yambowf':
            already_done = check_same_yambo(old, params_to_calc,k_mesh_to_calc,what,up_to_p2y=up_to_p2y)        
        if already_done: break
            
    for old in YamboWorkflow_group.nodes:
        if old.process_type == 'aiida.workflows:yambo.yambo.yamboconvergence':
            for i in old.called:
                parent_nscf, parent_scf = check_same_pw(i, k_mesh_to_calc, already_done)
                if parent_nscf: break
        
        elif old.process_type == 'aiida.workflows:yambo.yambo.yambowf':
            parent_nscf = check_same_nscf(old, k_mesh_to_calc, already_done)
        
        if parent_nscf: break

    return already_done, parent_nscf, parent_scf  
    