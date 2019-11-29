# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
except:
    pass

################################################################################
################################################################################

class calc_manager_aiida: #the interface class to AiiDA... could be separated fro aiida and yambopy

    def __init__(self, calc_info={}):
        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

################################## update_parameters #####################################
    def updater(self, inp_to_update, k_distance, first):    #parameter list? yambopy philosophy

        if self.var == 'bands':
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params['BndsRnXp'][-1] = new_params['BndsRnXp'][-1] + self.delta*first
            new_params['GbndRnge'][-1] = new_params['GbndRnge'][-1] + self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params['GbndRnge'][-1]

        elif self.var == 'kpoints':
            k_distance = k_distance + self.delta*first

            inp_to_update.scf.kpoints = KpointsData()
            inp_to_update.scf.kpoints.set_cell(inp_to_update.scf.pw.structure.cell)
            inp_to_update.scf.kpoints.set_kpoints_mesh_from_density(1/k_distance, force_parity=True)
            inp_to_update.nscf.kpoints = inp_to_update.scf.kpoints

            try:
                del inp_to_update.parent_folder  #I need to start from scratch...
            except:
                pass

            value = k_distance

        elif self.var == 'cutoff':
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params['CUTBox'] = new_params['CUTBox'] + [1,1,1]*self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params['CUTBox'][-1]

        else: #"scalar" quantity
            new_params = inp_to_update.yres.gw.parameters.get_dict()
            new_params[str(self.var)] = new_params[str(self.var)] + self.delta*first

            inp_to_update.yres.gw.parameters = Dict(dict=new_params)

            value = new_params[str(self.var)]

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
                if what == 'gap': #datasets from parser????
                    quantities[j,i-1,1] = abs((yambo_calc.outputs.array_qp.get_array('Eo')[(where[j][1]-1)*2+1]+
                                yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[(where[j][1]-1)*2+1]-
                                (yambo_calc.outputs.array_qp.get_array('Eo')[(where[j][0]-1)*2]+
                                yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[(where[j][0]-1)*2])))

                if what == 'single-levels':
                    quantities[j,i-1,1] = yambo_calc.outputs.array_qp.get_array('Eo')[where[j]-1]+ \
                                yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[where[j]-1]

                quantities[j,i-1,0] = i*self.delta  #number of the iteration times the delta... to be used in a fit
                quantities[j,i-1,2] = int(yambo_calc.pk) #CalcJobNode.pk

        return quantities


######################### AiiDA specific #############################

    def get_caller(self, calc, depth = 2):
        for i in range(depth):
            calc = load_node(calc).caller
        return calc

    def get_called(self, calc, depth = 2):
        for i in range(depth):
            calc = load_node(calc).called[0]
        return calc

    def start_from_converged(self, node, params):
        self.ctx.calc_inputs.yres.gw.parameters = node.get_builder_restart().yres.gw['parameters']

    def set_parent(self, last_ok):
        self.ctx.calc_inputs.parent_folder = last_ok.outputs.yambo_calc_folder

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
