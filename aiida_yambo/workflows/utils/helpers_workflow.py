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
                    starting_inputs[var] = inputs['variables'][var]

    return starting_inputs

def create_space(starting_inputs, workflow_dict, wfl_type='1D_convergence', hint= 1):
    
    space={}
    first = 0 
    for i in workflow_dict:
        l = i['var']
        delta=i['delta']*hint
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
                    if isinstance(delta[l.index(var)],int) or isinstance(delta[l.index(var)],float):
                        new_val = starting_inputs[var][0]+delta[l.index(var)]*(r+first-1)
                        if not 'mesh' in var:
                            new_val = [new_val, starting_inputs[var][1]]
                    elif isinstance(delta[l.index(var)],list): 
                        if not 'mesh' in var:
                            new_val = [sum(x) for x in zip(starting_inputs[var][0], [d*(r+first-1) for d in delta[l.index(var)]])]
                            new_val = [new_val, starting_inputs[var][1]]
                        else:
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

    #here should be a default list of convergence "parameters_space".

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
    
    copy_wfl_sett = copy.deepcopy(wfl_settings)
    workflow_dict['type'] = copy_wfl_sett.pop('type','1D_convergence')
    workflow_dict['what'] = copy_wfl_sett.pop('what','gap_')
    workflow_dict['convergence_algorithm'] = copy_wfl_sett.pop('convergence_algorithm', 'dummy')

    workflow_dict['global_step'] = 0
    workflow_dict['fully_success'] = False

    workflow_dict['starting_inputs'] = collect_inputs(inputs, kpoints, new_l)
    workflow_dict['parameter_space'] = create_space(workflow_dict['starting_inputs'], new_l, workflow_dict['type'])
    workflow_dict['to_be_parsed'] = []
    workflow_dict['wfl_pk'] = []
    return workflow_dict

@conversion_wrapper
def build_story_global(calc_manager, quantities, workflow_dict = {}):

    if calc_manager['iter'] == 1:
        try:
            workflow_dict['array_conv']=np.array(workflow_dict['workflow_story']\
                [workflow_dict['workflow_story']['useful'] == True].iloc[-1,])
            workflow_dict['array_conv'] = np.column_stack((workflow_dict['array_conv'],quantities[:,:,1]))
        except:
            workflow_dict['array_conv']=np.array(quantities[:,:,1])
    else:
        workflow_dict['array_conv'] = np.column_stack((workflow_dict['array_conv'],quantities[:,:,1]))

@conversion_wrapper
def update_story_global(calc_manager, quantities, inputs, workflow_dict):
        
    final_result = {}
    if workflow_dict['global_step'] == 0 :
        workflow_dict['workflow_story'] = pd.DataFrame(columns = ['global_step']+list(quantities.columns)+['parameters_studied']+\
                        ['useful','failed'])

    for i in range(calc_manager['steps']):
            workflow_dict['global_step'] += 1
            if isinstance(calc_manager['var'],list):
                separator = ', '
                var_names = separator.join(calc_manager['var'])
            else:
                var_names = calc_manager['var']

            workflow_story_list = [workflow_dict['global_step']]+quantities.values[i].tolist()+[var_names]+\
                        [True, False]

            workflow_df = pd.DataFrame([workflow_story_list], columns = ['global_step']+list(quantities.columns)+['parameters_studied']+\
                    ['useful','failed'])

            workflow_dict['workflow_story'] = workflow_dict['workflow_story'].append(workflow_df, ignore_index=True)
   
    for i in range(1,len(workflow_dict['workflow_story'])+1):
        try:                
            last_ok_uuid = workflow_dict['workflow_story'].iloc[-i]['uuid']
            #last_ok_wfl = get_caller(last_ok_uuid, depth = 1)
            start_from_converged(inputs, last_ok_uuid)
            if calc_manager['var'] == 'kpoint_mesh' or calc_manager['var'] == 'kpoint_density':
                set_parent(inputs, load_node(last_ok_uuid))
            break
        except:
            last_ok_uuid = workflow_dict['workflow_story'].iloc[-1]['uuid']
            #last_ok_wfl = get_caller(last_ok_uuid, depth = 1)
    
    workflow_dict['workflow_story'] = workflow_dict['workflow_story'].replace({np.nan:None})

    final_result={'uuid': last_ok_uuid,}
        
    return final_result

@conversion_wrapper
def post_analysis_update(inputs, calc_manager, oversteps, none_encountered, workflow_dict = {}, hint=None):
    
    final_result = {}
    for i in range(oversteps):
        workflow_dict['workflow_story'].at[workflow_dict['global_step']-1-i,'useful']=False
    if oversteps:
        for i in range(calc_manager['steps']*calc_manager['iter']-oversteps):
            for j in calc_manager['var']:
                workflow_dict['parameter_space'][j].pop(0)
    for i in none_encountered: 
            workflow_dict['workflow_story'].at[workflow_dict['global_step']-i,'failed']=True
            workflow_dict['workflow_story'].at[workflow_dict['global_step']-i,'useful']=False
    if len(none_encountered) > 0:
        for i in range(calc_manager['steps']*calc_manager['iter']-len(none_encountered)):
            for j in calc_manager['var']:
                workflow_dict['parameter_space'][j].pop(0)

    #try:
    if len(workflow_dict['workflow_story'][(workflow_dict['workflow_story']['useful'] == True) & (workflow_dict['workflow_story']['failed'] == False)]) > 0:
        last_ok_uuid = workflow_dict['workflow_story'][(workflow_dict['workflow_story']['useful'] == True) & (workflow_dict['workflow_story']['failed'] == False)].iloc[-1]['uuid']
        #last_ok_wfl = get_caller(last_ok_uuid, depth = 1)
        start_from_converged(inputs, last_ok_uuid)
    
        if calc_manager['var'] == 'kpoint_mesh' or calc_manager['var'] == 'kpoint_density':
            set_parent(inputs, load_node(last_ok_uuid))
    else: 
        final_result={}
    #except:
    #    last_ok_uuid = workflow_dict['workflow_story'].iloc[-1]['uuid']
    #    last_ok_wfl = get_caller(last_ok_uuid, depth = 1)

    
    workflow_dict['workflow_story'] = workflow_dict['workflow_story'].replace({np.nan:None})
    
    try:
        final_result={'uuid': last_ok_uuid,}
    except:
        final_result={}
        
    return final_result

################################################################################
############################## NEW convergence_evaluator ######################################

class Convergence_evaluator(): 
    
    def __init__(self, **kwargs): #lista_YamboIn, conv_array, parametri_da_conv(se lista fai fit multidimens), thr, window
        for k,v in kwargs.items():
            setattr(self, k, v)
        self.hint = {}
        self.extrapolated = 1
        if not hasattr(self,'power_law'): self.power_law = 1 
        
    def dummy_convergence(self): #solo window, thr e oversteps
        self.delta = self.conv_array-self.conv_array[-1]
        converged = self.delta[-self.window:][np.where(abs(self.delta[-self.window:])<=self.thr)]
        if len(converged)<self.window:
            is_converged = False
            oversteps = 0
            converged_result = None
        else:
            is_converged = True
            oversteps = len(converged)
            for overstep in range(self.window+1,len(self.delta)+1):
                overconverged = self.delta[-overstep:][np.where(abs(self.delta[-overstep:])<=self.thr)]
                if oversteps < len(overconverged):
                    oversteps = len(overconverged)
                else:
                    break     
            converged_result = self.conv_array[-oversteps]
            
        return self.delta, converged, is_converged, oversteps-1, converged_result
    
    def convergence_function(self,xv,*args): #con fit e previsione parametri a convergenza con la thr
        if isinstance(self.power_law,int): self.power_law = [self.power_law]*len(self.parameters)
        y = 1.0
        for i in range(len(xv)):
            A=args[2*i]
            B=args[2*i+1]
            xval=xv[i]
            y = y * ( A/xval + B)
        return y
    
    def convergence_prediction(self):  #1D
        extra, pcov = curve_fit(self.convergence_function,self.p,self.conv_array,p0=[1,1]*len(self.parameters))
        self.extra = extra
        print(extra)
        for i in range(len(self.parameters)):
            a = extra[2*i]
            b = extra[2*i+1]
            self.extrapolated = b*self.extrapolated
            f = lambda x: a/x**self.power_law[i]
            self.prediction = minimize(f,x0=self.p[i][-1],tol=3*1e-4,method='BFGS')
            print(self.prediction,'\n')
            self.hint[self.parameters[i]] = int(self.prediction.x[0])
            f_2 = lambda x: -a/x**(1+self.power_law[i])*self.power_law[i]
            print('grad renorm:',self.p[i][-1]*f_2(self.p[i][-1]))
            print('delta hint:',abs(self.p[-1][-1]*f_2(self.p[i][-1]))/self.thr,'\n') #ma é uguale a fun*100 ... ?
        
        return extra[1], self.fun

def prepare_for_ce(workflow_dict,keys=['gap_GG']):
    workflow_story = workflow_dict # pd.DataFrame.from_dict(workflow_dict['workflow_story']) 
    real = workflow_story
    lines = {}
    for k in ['BndsRnXp','GbndRnge','NGsBlkXp','kpoint_mesh']: #to be generalized
        if k in ['BndsRnXp','GbndRnge']:
            lines[k] = np.array([i[0] for i in zip(list(real[k].values))])[:,1]
        elif k in ['kpoint_mesh']:
            lines[k] = np.array([i[0] for i in zip(list(real[k].values))])[:,0]
            for i in range(1,3):
                lines[k] *= np.array([i[0] for i in zip(list(real[k].values))])[:,i]
        else:
            lines[k] = np.array([i for i in zip(list(real[k].values))])[:,0]
    homo = {}
    for key in keys:
        homo[key] = real[key].values

    return real,lines,homo

@conversion_wrapper
def analysis_and_decision(calc_dict, workflow_dict={}):
    steps = calc_dict['steps']*calc_dict['iter']+1
    if len(calc_dict['var'])>1:
        var=calc_dict['var'][0]
    else:
        var=calc_dict['var']

    if isinstance(workflow_dict['what'][-1],list):
        what=workflow_dict['what'][0]
    else:
        what=workflow_dict['what']

     
    real,lines,homo = prepare_for_ce(workflow_dict['workflow_story'][workflow_dict['workflow_story'].failed==False][-steps:],)
    y = Convergence_evaluator(conv_array=homo[what], 
                                thr=calc_dict['conv_thr'], 
                                window=calc_dict['conv_window'], 
                                parameters=[var], 
                                p=[lines[var],])
    
    none_encountered = list(workflow_dict['workflow_story'][-steps:][workflow_dict['workflow_story'].failed==True].global_step)
    
    delta, converged, is_converged, oversteps, converged_result = y.dummy_convergence()

    if workflow_dict['convergence_algorithm'] == 'smart':
        predicted, hint = y.convergence_prediction()
        if hint < 1:
            hint = hint*100
        else:
            hint = 1
    else:
        predicted, hint = converged_result, 1

    return is_converged, oversteps, none_encountered, hint    
    



###############################  parallelism  ####################################

def build_parallelism_instructions(instructions):

    instructions['automatic'] = instructions.pop('automatic', False)
    instructions['semi-automatic'] = instructions.pop('semi-automatic', False)
    instructions['manual'] = instructions.pop('manual', False)
    instructions['function'] = instructions.pop('function', False)

    return instructions