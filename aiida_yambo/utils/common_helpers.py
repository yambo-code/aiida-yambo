# -*- coding: utf-8 -*-
"""helpers for many purposes"""
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


def find_parent(calc):

    try:
        parent_calc = calc.inputs.parent_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
    except:
        parent_calc = calc.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
    return parent_calc

def find_pw_parent(parent_calc, calc_type = 'nscf'):

    has_found_pw = False
    while (not has_found_pw):
        if parent_calc.process_type=='aiida.calculations:yambo.yambo':
            has_found_pw = False
            parent_calc = find_parent(parent_calc)
            if parent_calc.process_type=='aiida.calculations:quantumespresso.pw' and \
                find_pw_type(parent_calc) == calc_type:
                has_found_pw = True
            else:
                parent_calc = find_parent(parent_calc)
        elif parent_calc.process_type=='aiida.calculations:quantumespresso.pw' and \
            find_pw_type(parent_calc) == calc_type:
            has_found_pw = True
        else:
            parent_calc = find_parent(parent_calc)

    return parent_calc

def get_distance_from_kmesh(calc):
    mesh = calc.inputs.kpoints.get_kpoints_mesh()[0]
    k = KpointsData()
    k.set_cell(calc.inputs.structure.cell)
    for i in range(1,100):
         k.set_kpoints_mesh_from_density(1/i)
         if k.get_kpoints_mesh()[0]==mesh:
             print('ok, {} is the density'.format(i))
             print(k.get_kpoints_mesh()[0],mesh)
             return i

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


def update_dict(_dict, what, how):
    new = _dict.get_dict()
    new[what] = how
    _dict = Dict(dict=new)
    return _dict

def get_caller(calc_pk, depth = 1):
     for i in range(depth):
         calc = load_node(int(calc_pk))
         calc = calc.caller.caller
     return calc

def get_called(calc, depth = 2):
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
