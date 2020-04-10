# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from aiida_yambo.utils.common_helpers import *
############################# AiiDA - independent ################################

class workflow_manager:

    def __init__(self, parameters_space, wfl_settings):

        try:
            #AiiDA calculation --> this is the only AiiDA dependence of the class...the rest is abstract
            ps = parameters_space.get_list()
            ps.reverse()
            self.ideal_iter = copy.deepcopy(ps)
            self.true_iter = copy.deepcopy(ps)
            self.type = 'AiiDA_calculation'
            #from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA_calculation'
            #from helpers_yambopy import calc_manager_yambopy as calc_manager     #qe py?
            self.ideal_iter = copy.deepcopy(parameters_space)
            self.true_iter = copy.deepcopy(parameters_space)

        self.type = wfl_settings['type']

    def build_story_global(self, calc_manager, quantities):

        if calc_manager.iter == 1:
            try:
                self.array_conv=np.array(self.conv_story[-1][-1])
                self.array_conv = np.column_stack((self.array_conv,quantities[:,:,1]))
            except:
                self.array_conv=np.array(quantities[:,:,1])
        else:
            self.array_conv = np.column_stack((self.array_conv,quantities[:,:,1]))

    def update_story_global(self, calc_manager, quantities):

        if self.first_calc:
            self.workflow_story = []
            self.workflow_story.append(['global_step']+list(calc_manager.__dict__.keys())+\
                        ['value', 'calc_pk','result_eV','useful'])
            #self.first_calc = False

        for i in range(calc_manager.steps):
                self.global_step += 1
                self.workflow_story.append([self.global_step]+list(calc_manager.__dict__.values())+\
                            [self.values[i], quantities[0,i,2], quantities[:,i,1], True])

    def post_analysis_update(self,inputs, calc_manager, oversteps):

        final_result = {}

        for i in range(oversteps):
            self.workflow_story[-(i+1)][-1]=False

        last_ok_wfl = get_caller(self.workflow_story[-(oversteps+1)][-3], depth = 1)
        calc_manager.start_from_converged(inputs, last_ok_wfl)

        if calc_manager.var == 'kpoints':
            set_parent(inputs, load_node(self.workflow_story[-(oversteps+1)][-3]))

        final_result={'calculation_pk': int(self.workflow_story[-(oversteps+1)][-3]),\
                    'result_eV':self.workflow_story[-(oversteps+1)][-2],'success':self.workflow_story[-(oversteps+1)][-1]}

        return final_result

################################################################################
############################## convergence_evaluator ######################################

class the_evaluator:

    def __init__(self, infos):

        self.infos = infos

    def analysis_and_decision(self, quantities):

        if self.infos.type == '1D_convergence':
            '''documentation...'''
            self.window =  self.infos.conv_window
            self.tol = self.infos.conv_thr
            converged = True
            oversteps = 0

            for i in range(2,len(quantities[0,:])+1): #check it
                if np.max(abs(quantities[:,-1]-quantities[:,-i])) < self.tol: #backcheck
                    oversteps = i-1
                else:
                    print(abs(quantities[:,-1]-quantities[:,-i]),quantities[:,-i])
                    break
            if oversteps < self.window-1:
                converged = False

            return converged, oversteps

        if self.infos.type == '2D_space':
            '''documentation...'''

            return True, 0


################################################################################
