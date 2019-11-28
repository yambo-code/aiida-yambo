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

class calc_manager: #the interface class to AiiDA

    def __init__(self, calc_info):

        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

        try: #AiiDA calculation
            self.type = str(self.take_down().get_description).split()[-1] #not working now
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA'

################################## update_parameters #####################################
    def updater(self, inp_to_update, k_distance, first):    #parameter list? yambopy philosophy

        if self.type == 'not_AiiDA':
            pass
        else:    #aiida_yambo_conv_updater()...
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

        if self.type == 'not_AiiDA':
            pass  #yambopy

        else:

            if 'quantumespresso.pw' in self.type:
                print('from conv_utils.')
            if 'yambo.yambo' in self.type:
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

#######################################################
    def get_caller(self, calc, depth = 2):

        for i in range(depth):

            if self.type == 'not_AiiDA':
                pass  #yambopy
            else:
                calc = load_node(calc).caller

        return calc

    def update_converged_parameters(self, node, params):

        if self.type == 'not_AiiDA':
            pass  #yambopy

        else:
            self.ctx.calc_inputs.yres.gw.parameters = node.get_builder_restart().yres.gw['parameters']


######################### AiiDA specific #############################
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

################################################################################
############################# AiiDA - independent - another file !?################################

class workflow_manager:

    def __init__(self, conv_opt):

        try: #AiiDA calculation --> this is the only AiiDA dependence of the class...the rest is abstract
            self.ideal_iter = copy.deepcopy(conv_opt.get_list())
            self.true_iter = copy.deepcopy(conv_opt.get_list())
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA'
            self.ideal_iter = copy.deepcopy(conv_opt)
            self.true_iter = copy.deepcopy(conv_opt)

    def build_story_global(self, calc_manager):

        quantities = calc_manager.take_quantities()

        if calc_manager.iter == 1:
            try:
                self.array_conv=np.array(self.conv_story[-1][-1])
                self.array_conv = np.column_stack((self.array_conv,quantities[:,:,1]))
            except:
                self.array_conv=np.array(quantities[:,:,1])
        else:
            self.array_conv = np.column_stack((self.array_conv,quantities[:,:,1]))

    def update_story_global(self,calc_manager):

        if self.first_calc:
            self.absolute_story.append(['global_step']+list(calc_manager.__dict__.keys())+\
                        ['value', 'calc_pk','result'])
            self.conv_story.append(['global_step']+list(calc_manager.__dict__.keys())+\
                        ['value', 'calc_pk','result'])
            self.first_calc = False

        for i in range(calc_manager.steps):
                self.global_step += 1
                self.absolute_story.append([self.global_step]+list(calc_manager.__dict__.values())+\
                            [self.values[i], quantities[0,i,2], quantities[:,i,1]])
                self.conv_story.append([self.global_step]+list(calc_manager.__dict__.values())+\
                            [self.values[i], int(quantities[0,i,2]), quantities[:,i,1]])

    def update_convergence_story(self,calc_manager,oversteps):

        self.conv_story = self.ctx.workflow_manager.conv_story[:-oversteps]

        parent_folder = calc_manager.get_caller(self.conv_story[-1][-2], depth = 2)
        calc_manager.update_converged_parameters(parent_folder) 

        if calc_manager.var == 'kpoints':
            #self.ctx.calc_inputs.parent_folder = last_ok.outputs.yambo_calc_folder
            calc_manager.set_parent(parent_folder)

        if calc_manager.var == 'kpoints':
            k_distance = k_distance - calc_manager.delta*oversteps
################################################################################
############################## convergence_evaluator ######################################

class the_evaluator:

    def __init__(self, window = 3, tol = 1e-3):

        self.window = window
        self.tol = tol

    def convergence_and_backtracing(self, quantities):

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


################################################################################
################################## plots&tables #####################################
class workflow_inspector:

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
