# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

#to import it:
#sys.path.append('/home/mbonacci/Documents/aiida_1_tests/scripts/protocols')
#from classes import *

try:
    from aiida.orm import Dict, Str, load_node
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
            self.type = str(self.take_down().get_description).split()[-1]
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA'
            pass
################################## update_parameters #####################################
    def updater(self, inp_to_update, k_distance, first):    #mettere supporto anche x lista di parametri, non solo aumento cosi'...

        if self.type == 'not_AiiDA':
            pass
        else:
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

                self.report('Mesh used: {} \nfrom density: {}'\
                    .format(inp_to_update.scf.kpoints.get_kpoints_mesh(),1/k_distance))

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
            pass  #implementerò poi.. ho già qualcosina, almeno per yambo...x qe mi basta estrarre etot e le strutture(con ase da output!!)

        else:

            if 'quantumespresso.pw' in self.type:
                print('quindi mi cerco la etot o una struttura... procedura da specificare, ma cmq ho tutto in conv_utils.')
            if 'yambo.yambo' in self.type:
                print('sto cercando {} per i kpoints {}'.format(what,where))

                quantities = np.zeros((len(where),backtrace,3))

                for j in range(len(where)): #no steps*self.iter xk in teoria voglio andare x steps
                    for i in range(1,backtrace+1): #qui devo capire come generalizzare in caso di wfl o superwfl o simple calc
                        yambo_calc = load_node(self.wfl_pk).caller.called[backtrace-i].called[0].called[0]
                        if what == 'gap': #bisognerebbe cambiare come parsa parser.py, fa schifo cosi': dovrei fare per k e per bande...
                            quantities[j,i-1,1] = abs((yambo_calc.outputs.array_qp.get_array('Eo')[(where[j][1]-1)*2+1]+
                                        yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[(where[j][1]-1)*2+1]-
                                        (yambo_calc.outputs.array_qp.get_array('Eo')[(where[j][0]-1)*2]+
                                        yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[(where[j][0]-1)*2])))

                        if what == 'single-levels':
                            quantities[j,i-1,1] = yambo_calc.outputs.array_qp.get_array('Eo')[where[j]-1]+ \
                                        yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[where[j]-1]

                        quantities[j,i-1,0] = i*self.delta  #number of the iteration times the delta... to be used in a fit
                        quantities[j,i-1,2] = int(yambo_calc.pk) #CalcJobNode.pk responsible of the calculation

                return quantities

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
############################# Astratti da AiiDA ##################################

class workflow_manager:

    def __init__(self, conv_opt):

        try: #AiiDA calculation --> this is the only AiiDA dependence of the class...the remaining is abstract
            self.ideal_iter = copy.deepcopy(conv_opt.get_list())
            self.true_iter = copy.deepcopy(conv_opt.get_list())
        except:
            #this is not an AiiDA calculation
            self.type = 'not_AiiDA'
            self.ideal_iter = copy.deepcopy(conv_opt)
            self.true_iter = copy.deepcopy(conv_opt)
            pass

        self.absolute_story = []
        self.conv_story = [] #se dalla absolute story mi metto una flag: conv_path che mi distingue conv_path da abs_path? meglio eh!!

    def update_story(self, iter_info):
        self.absolute_story = self.absolute_story
        self.conv_story

################################################################################
############################## convergence_evaluator ######################################

class the_evaluator: #astratto totalmente da AiiDA

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
