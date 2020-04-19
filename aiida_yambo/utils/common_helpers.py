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
    from aiida.orm import Dict, Str, List, load_node, KpointsData, RemoteData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida.engine import calcfunction 
except:
    pass


def find_parent(calc):

    try:
        parent_calc = calc.inputs.parent_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
    except:
        parent_calc = calc.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
    return parent_calc

def find_pw_parent(parent_calc, calc_type = ['scf', 'nscf']):

    has_found_pw = False
    while (not has_found_pw):
        if parent_calc.process_type=='aiida.calculations:yambo.yambo':
            has_found_pw = False
            parent_calc = find_parent(parent_calc)
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


def update_dict(_dict, whats, hows):
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

def find_gw_info(calc):

    parameters = calc.inputs.parameters.get_dict()
    
    ## bands ##
    BndsRnXp = parameters.pop('BndsRnXp')
    GbndRnge = parameters.pop('GbndRnge')
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
    for i in parameters['QPkrange']:
        qp += (1 + i[1]-i[0])*(1 + i[3]-i[2])
        last_qp = max(i[3],last_qp)

    ## runlevels ##
    runlevels = []
    for i in parameters.keys():
        if parameters[i] == True:
            runlevels.append(i)
    
    return bands, qp, last_qp, runlevels
        