# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

############################# AiiDA - independent ################################

class workflow_manager:

    def __init__(self, parameters_space, wfl_type = ' '):

        try:
            #AiiDA calculation --> this is the only AiiDA dependence of the class...the rest is abstract
            self.ideal_iter = copy.deepcopy(parameters_space.get_list())
            self.true_iter = copy.deepcopy(parameters_space.get_list())
            self.type = 'AiiDA_calculation'
            #from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA_calculation'
            #from helpers_yambopy import calc_manager_yambopy as calc_manager     #qe py?
            self.ideal_iter = copy.deepcopy(parameters_space)
            self.true_iter = copy.deepcopy(parameters_space)

        self.wfl_type = wfl_type

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
                        ['value', 'calc_pk','result (eV)','useful'])
            #self.first_calc = False

        for i in range(calc_manager.steps):
                self.global_step += 1
                self.workflow_story.append([self.global_step]+list(calc_manager.__dict__.values())+\
                            [self.values[i], quantities[0,i,2], quantities[:,i,1], True])

    def post_analysis_update(self,inputs, calc_manager, oversteps):

        for i in range(oversteps):
            self.workflow_story[-(i+1)][-1]=False

        last_ok_wfl = calc_manager.get_caller(self.workflow_story[-(oversteps+1)][-3], depth = 1)
        calc_manager.start_from_converged(inputs, last_ok_wfl)

        if calc_manager.var == 'kpoints':
            calc_manager.set_parent(inputs, last_ok_wfl)
            k_distance = k_distance - calc_manager.delta*oversteps


################################################################################
############################## convergence_evaluator ######################################

class the_evaluator:

    def __init__(self, infos):

        self.infos = infos

    def analysis_and_decision(self, quantities):

        if self.infos.wfl_type == '1D_convergence':
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

        if self.infos.wfl_type == '2D_space':
            '''documentation...'''

            return True, 0


################################################################################
################################## plots&tables #####################################
class workflow_inspector: #not working.

    def __init__(self, conv_info):

        pass

    def conv_plotter(self, all_list, conv_list, what = 'ciao', save = False):

        all_story =  pd.DataFrame(all_list)
        conv_story =  pd.DataFrame(conv_list)

        conv_story_array = conv_story.to_numpy()

        fig,ax = plt.subplots()
        plt.xlabel('iteration')
        plt.ylabel(what)
        plt.grid()

        plt.title('Convergence of {}, pk = {}'.format(what,wfl_pk))
        ax.plot(all_story['global_step'],all_story[what],'*--',label='all calculations')
        ax.plot(conv_story['global_step'],conv_story[what],label='convergence path')

        b=[]

        for i in conv_story['var']:
            if i not in b:
                a = np.ma.masked_where(conv_story_array[:,0]!=str(i),conv_story_array[:,9])
                ax.plot(conv_story['global_step'],a,'*-',label=str(i)+' - '+str(conv_story['value'][conv_story['var']==i].to_numpy()[-1]))
                b.append(i)
        plt.legend()

        if save == True:
            plt.savefig(str(wfl_pk)+"_"+str(what)+".pdf",dpi=300)

    def conv_table(self, save = False):
        pass
        if save == True:
            plt.savefig(str(wfl_pk)+"_"+str(what)+"_table.pdf",dpi=300)
