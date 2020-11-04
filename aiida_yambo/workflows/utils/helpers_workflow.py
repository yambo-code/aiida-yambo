# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from aiida_yambo.workflows.utils.helpers_aiida_yambo import *
from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
from aiida_yambo.utils.common_helpers import *
############################# AiiDA - independent ################################

#class convergence_workflow_manager:
def conversion_wrapper(func):
    def wrapper(*args, workflow_dict = {}):

        try: 
            workflow_dict['array_conv'] = np.array(workflow_dict['array_conv']) 
        except: 
            pass
        try: 
            workflow_dict['workflow_story'] = pd.DataFrame.from_dict(workflow_dict['workflow_story']) 
        except: 
            pass
        output = func(*args, workflow_dict = workflow_dict)
        try: 
            workflow_dict['array_conv'] = workflow_dict['array_conv'].tolist()
        except: 
            pass
        try: 
            workflow_dict['workflow_story'] = workflow_dict['workflow_story'].to_dict() 
        except: 
            pass
        
        return output

    return wrapper

def convergence_workflow_manager(parameters_space, wfl_settings):
    workflow_dict = {}
    try:
        #AiiDA calculation --> this is the only AiiDA dependence of the class...the rest is abstract
        ps = parameters_space.get_list()
        ps.reverse()
        workflow_dict['ideal_iter'] = copy.deepcopy(ps)
        workflow_dict['true_iter'] = copy.deepcopy(ps)
        workflow_dict['type'] = 'AiiDA_calculation'
        #from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
    except:
        #this is not an AiiDA calculation
        workflow_dict['type'] = 'not_AiiDA_calculation'
        #from helpers_yambopy import calc_manager_yambopy as calc_manager     #qe py?
        workflow_dict['ideal_iter'] = copy.deepcopy(parameters_space)
        workflow_dict['true_iter'] = copy.deepcopy(parameters_space)
    
    workflow_dict['type'] = wfl_settings['type']

    workflow_dict['global_step'] = 0
    workflow_dict['fully_success'] = False
    workflow_dict['first_calc'] = True

    return workflow_dict

@conversion_wrapper
def build_story_global(calc_manager, quantities, workflow_dict = {}):

    if calc_manager['iter'] == 1:
        try:
            workflow_dict['array_conv']=np.array(workflow_dict['workflow_story']\
                [workflow_dict['workflow_story']['useful'] == True].iloc[-1]['result_eV'])
            workflow_dict['array_conv'] = np.column_stack((workflow_dict['array_conv'],quantities[:,:,1]))
        except:
            workflow_dict['array_conv']=np.array(quantities[:,:,1])
    else:
        workflow_dict['array_conv'] = np.column_stack((workflow_dict['array_conv'],quantities[:,:,1]))

@conversion_wrapper
def update_story_global(calc_manager, quantities, inputs, workflow_dict = {}):
        
    final_result = {}
    if workflow_dict['global_step'] == 0 :
        workflow_dict['workflow_story'] = pd.DataFrame(columns = ['global_step']+list(calc_manager.keys())+\
                        ['value', 'calc_pk','result_eV','useful','failed'])

    for i in range(calc_manager['steps']):
            workflow_dict['global_step'] += 1
            workflow_story_list = [workflow_dict['global_step']]+list(calc_manager.values())+\
                        [workflow_dict['values'][i], quantities[0,i,2], quantities[:,i,1].tolist(), True, False]
            workflow_df = pd.DataFrame([workflow_story_list],columns = ['global_step']+list(calc_manager.keys())+\
                    ['value', 'calc_pk','result_eV','useful','failed'])
            workflow_dict['workflow_story'] = workflow_dict['workflow_story'].append(workflow_df, ignore_index=True)

    for i in range(1,len(workflow_dict['workflow_story'])+1):
        try:                
            last_ok_pk = int(workflow_dict['workflow_story'].iloc[-i]['calc_pk'])
            last_ok_wfl = get_caller(last_ok_pk, depth = 1)
            start_from_converged(inputs, last_ok_wfl)
            break
        except:
            pass
    
    if calc_manager['var'] == 'kpoints':
        set_parent(inputs, load_node(last_ok_pk))

    final_result={'calculation_uuid': load_node(last_ok_pk).uuid,\
            'result_eV':workflow_dict['workflow_story'].iloc[-1]['result_eV'],\
                'success':workflow_dict['workflow_story'].iloc[-1]['useful']}
        
    return final_result

@conversion_wrapper
def post_analysis_update(inputs, calc_manager, oversteps, none_encountered, workflow_dict = {}):
    
    final_result = {}
    for i in range(oversteps):
        workflow_dict['workflow_story'].at[workflow_dict['global_step']-1-i,'useful']=False
        if none_encountered:
            workflow_dict['workflow_story'].at[workflow_dict['global_step']-1-i,'failed']=True

    last_ok_pk = int(workflow_dict['workflow_story'][workflow_dict['workflow_story']['useful'] == True].iloc[-1]['calc_pk'])
    last_ok_wfl = get_caller(last_ok_pk, depth = 1)
    start_from_converged(inputs, last_ok_wfl)
        
    if calc_manager['var'] == 'kpoint_mesh' or calc_manager['var'] == 'kpoint_density' :
        set_parent(inputs, load_node(last_ok_pk))
    
    final_result={'calculation_uuid': load_node(last_ok_pk).uuid,\
                'result_eV':workflow_dict['workflow_story'][workflow_dict['workflow_story']['useful'] == True].iloc[-1]['result_eV'],\
                    'success':bool(workflow_dict['workflow_story'][workflow_dict['workflow_story']['useful'] == True].iloc[-1]['useful'])}

    workflow_dict['workflow_story'] = workflow_dict['workflow_story'].replace({np.nan:None})

    return final_result

################################################################################
############################## convergence_evaluator ######################################

class the_evaluator:

    def __init__(self, infos):

        self.infos = infos

    def analysis_and_decision(self, quantities):
        quantities = np.array(quantities)
        if self.infos['type'] == '1D_convergence':
            '''documentation...'''
            self.window =  self.infos['conv_window']
            self.tol = self.infos['conv_thr']
            converged = True
            oversteps = 0
            none_encountered = False

            for j in range(1,len(quantities[0,:])+1):
                if quantities[0,-j] == False:
                    converged = False
                    oversteps +=1
                    none_encountered = True
            
            if none_encountered:
                return converged, oversteps, none_encountered

            for i in range(2,len(quantities[0,:])+1): #check it
                if np.max(abs(quantities[:,-1]-quantities[:,-i])) < self.tol: #backcheck
                    oversteps = i-1
                else:
                    print(abs(quantities[:,-1]-quantities[:,-i]),quantities[:,-i])
                    break
            if oversteps < self.window-1:
                converged = False

            return converged, oversteps, none_encountered

        if self.infos['type'] == '2D_space':
            '''documentation...'''

            return True, 0


################################################################################
