# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
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

def collect_inputs(inputs, kpoints, ideal_iter):
    
    starting_inputs = {}
    for i in ideal_iter:
        #print(i)
        l = i['var']
        delta=i['delta']
        if not isinstance(i['var'],list):
            l=[i['var']]
        if not isinstance(i['delta'],list) or 'mesh' in i['var']:
            delta=[i['delta']]
        for var in l:
            #print(var)
            if var not in starting_inputs.keys():
                if 'mesh' in var:
                    starting_inputs[var] = kpoints.get_kpoints_mesh()[0]
                else:
                    starting_inputs[var] = inputs[var]

    return starting_inputs

def create_space(starting_inputs, workflow_dict, wfl_type='1D_convergence'):
    
    space={}
    first = 0 
    for i in workflow_dict:
        #print(i)
        l = i['var']
        delta=i['delta']
        if not isinstance(i['var'],list):
            l=[i['var']]
        if not isinstance(i['delta'],list) or 'mesh' in i['var']:
            delta=[i['delta']]
        for var in l:
            #print(var)
            
            if var not in space.keys():
                space[var] = []
            else:
                starting_inputs[var]=space[var][-1]
            if wfl_type == '1D_convergence':
                for r in range(1,i['steps']*i['max_iterations']+1):
                    if isinstance(delta[l.index(var)],int):
                        new_val = starting_inputs[var]+delta[l.index(var)]*(r+first-1)
                    elif isinstance(delta[l.index(var)],list): 
                        new_val = [sum(x) for x in zip(starting_inputs[var], [d*(r+first-1) for d in delta[l.index(var)]])]
                    
                    space[var].append(new_val)
                    #print(new_val)
            else:
                for r in range(len(i['space'])):
                    new_val = i['space'][r][l.index(var)]
                
                    space[var].append(new_val)
        first = 1

    #print('Dimensions:')
    #print('bands_max: ',space['BndsRnXp'][-1][-1])
    #print('G_max: ',space['NGsBlkXp'][-1],' Ry')
    #m = space['kpoint_mesh'][-1]
    #print('kpts_max: ',m[0]*m[1]*m[2])

    return space


def convergence_workflow_manager(parameters_space, wfl_settings, inputs, kpoints):

    workflow_dict = {}
    new_l = []

    for i in parameters_space.get_list():
        new_conv = copy.deepcopy(i)
        new_conv['max_iterations'] = i.pop('max_iterations', 3)
        new_conv['delta'] = i.pop('delta', 5)
        new_conv['steps'] = i.pop('steps', 3)
        new_conv['conv_thr'] = i.pop('conv_thr', 0.05)
        new_l.append(new_conv)
    

    #AiiDA calculation --> this is the only AiiDA dependence of the class...the rest is abstract
    ps = copy.deepcopy(new_l)
    ps.reverse()
    workflow_dict['ideal_iter'] = copy.deepcopy(ps)
    workflow_dict['true_iter'] = copy.deepcopy(ps)
    workflow_dict['type'] = 'AiiDA_calculation'
    
    workflow_dict['type'] = wfl_settings['type']

    workflow_dict['global_step'] = 0
    workflow_dict['fully_success'] = False

    workflow_dict['starting_inputs'] = collect_inputs(inputs, kpoints, new_l)
    workflow_dict['parameter_space'] = create_space(workflow_dict['starting_inputs'], new_l, workflow_dict['type'])

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
            if calc_manager['var'] == 'kpoint_mesh' or calc_manager['var'] == 'kpoint_density':
                set_parent(inputs, load_node(last_ok_pk))
            break
        except:
            pass

    final_result={'calculation_uuid': load_node(last_ok_pk).uuid,\
            'result_eV':workflow_dict['workflow_story'].iloc[-1]['result_eV'],\
                'success':bool(workflow_dict['workflow_story'].iloc[-1]['useful'])}
        
    return final_result

@conversion_wrapper
def post_analysis_update(inputs, calc_manager, oversteps, none_encountered, workflow_dict = {}):
    
    final_result = {}
    for i in range(oversteps):
        workflow_dict['workflow_story'].at[workflow_dict['global_step']-1-i,'useful']=False
    for i in range(none_encountered): 
            workflow_dict['workflow_story'].at[workflow_dict['global_step']-1-i,'failed']=True

    last_ok_pk = int(workflow_dict['workflow_story'][(workflow_dict['workflow_story']['useful'] == True) & (workflow_dict['workflow_story']['failed'] == False)].iloc[-1]['calc_pk'])
    last_ok_wfl = get_caller(last_ok_pk, depth = 1)
    start_from_converged(inputs, last_ok_wfl)
        
    if calc_manager['var'] == 'kpoint_mesh' or calc_manager['var'] == 'kpoint_density':
        set_parent(inputs, load_node(last_ok_pk))
    
    final_result={'calculation_uuid': load_node(last_ok_pk).uuid,\
                'result_eV':workflow_dict['workflow_story'][(workflow_dict['workflow_story']['useful'] == True) & (workflow_dict['workflow_story']['failed'] == False)].iloc[-1]['result_eV'],\
                    'success':bool(workflow_dict['workflow_story'][(workflow_dict['workflow_story']['useful'] == True) & (workflow_dict['workflow_story']['failed'] == False)].iloc[-1]['useful'])}

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
            oversteps_1 = 0
            none_encountered = 0

            for j in range(1,len(quantities[0,:])+1):
                if quantities[0,-j].all() == False:
                    none_encountered +=1

            for i in range(none_encountered + 2, len(quantities[0,:])+1): #check it
                if np.max(abs(quantities[:,-(1+none_encountered)]-quantities[:,-i])) < self.tol: #backcheck
                    oversteps_1 = i-1
                else:
                    print(abs(quantities[:,-(1+none_encountered)]-quantities[:,-i]),quantities[:,-i])
                    break

            if oversteps_1 < self.window-1:
                converged = False

            return converged, oversteps_1, none_encountered

        if self.infos['type'] == '2D_space':
            '''documentation...'''

            return True, 0, 0


###############################  parallelism  ####################################

def build_parallelism_instructions(instructions):

    instructions['automatic'] = instructions.pop('automatic', False)
    instructions['semi-automatic'] = instructions.pop('semi-automatic', False)
    instructions['manual'] = instructions.pop('manual', False)
    instructions['function'] = instructions.pop('function', False)

    return instructions