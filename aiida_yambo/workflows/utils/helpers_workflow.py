# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis."""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit, minimize
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

def create_space(starting_inputs={}, workflow_dict={}, wfl_type='1D_convergence',hint=None):
    
    space={}
    first = 0 
    if not hint:
        hint = 1
    for i in workflow_dict:
        l = i['var']
        if 'delta' in i.keys(): delta=i['delta']*hint
        if 'commensurate' in i.keys(): delta=i['commensurate']
        # if 'explicit' in ... :
            #for new_val in i['explicit']:
            #    space[var].append(new_val)
            
            #continue
        
        if not isinstance(i['var'],list):
            l=[i['var']]
        if not isinstance(delta,list) or 'mesh' in i['var']:
            delta=[delta]
        for var in l:
            #print(var)
            
            if var not in space.keys():
                space[var] = []
            else:
                starting_inputs[var]=space[var][-1]
            if wfl_type == '1D_convergence' and 'delta' in i.keys() and not 'commensurate' in i.keys():
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
            elif wfl_type == '1D_convergence' and 'commensurate' in i.keys():
                for r in range(1,i['steps']*i['max_iterations']+1):
                    if first == 0: first = 1
                    if 'mesh' in var:
                            new_val = [a*b for a,b in zip(starting_inputs[var], [delta[l.index(var)]*(r+first-1),
                                                                                 delta[l.index(var)]*(r+first-1),
                                                                                 delta[l.index(var)]*(r+first-1)])]
                    elif isinstance(starting_inputs[var][0],int) or isinstance(starting_inputs[var][0],float):
                        new_val = starting_inputs[var][0]*delta[l.index(var)]*(r+first-1)
                        if not 'mesh' in var:
                            new_val = [new_val, starting_inputs[var][1]]
                    elif isinstance(starting_inputs[var][0],list): 
                        if not 'mesh' in var:
                            new_val = [a*b for a,b in zip(starting_inputs[var][0], [d*(r+first-1) for d in delta[l.index(var)]])]
                            new_val = [new_val, starting_inputs[var][1]]
                        
                    space[var].append(new_val)
                    #print(new_val)
            else:
                for r in range(len(i['space'])):
                    new_val = i['space'][r][l.index(var)]
                
                    space[var].append(new_val)
        first = 1

    return space

def update_space(starting_inputs={}, calc_dict={}, wfl_type='1D_convergence',hint=0,
                 existing_inputs={},convergence_algorithm='smart',
                 ):
    
    space={}
    
    first = 1
    if existing_inputs: starting_inputs = copy.deepcopy(existing_inputs)
    if convergence_algorithm == 'smart':
        factor = 1 # (calc_dict['iter']**0.5)
    elif convergence_algorithm == 'aggressive':
        factor = (calc_dict['iter']**0.5) + 1
    elif convergence_algorithm == 'dummy':
        factor = 0

    hint_ = int(hint*factor)
        
    for j in [1]:
        
        l = calc_dict['var']
        i = calc_dict
        if 'delta' in i.keys(): delta=i['delta']
        if 'commensurate' in i.keys(): delta=i['commensurate']
        # if 'explicit' in ... :
            #for new_val in i['explicit']:
            #    space[var].append(new_val)
            
            #continue
        if not isinstance(i['var'],list):
            l=[i['var']]
        if not isinstance(delta,list) or 'mesh' in i['var']:
            delta=[delta]
        for var in l:  
            starting_inputs[var] =  starting_inputs[var][i['steps']-1]
            if var not in space.keys():
                space[var] = []
            else:
                starting_inputs[var]=space[var][-1]
            if 'delta' in i.keys() and not 'commensurate' in i.keys():
                #for r in range(1,i['steps']*i['max_iterations']+1):
                for r in range(-i['steps']+1,len(existing_inputs[var])-i['steps']+1):
                    if r <= 0: 
                        new_val = existing_inputs[var][i['steps']+r-1]
                    elif isinstance(delta[l.index(var)],int) or isinstance(delta[l.index(var)],float):
                        new_val = starting_inputs[var][0]+delta[l.index(var)]*(r+first-1)*(1+hint_)
                        if not 'mesh' in var:
                            new_val = [new_val, starting_inputs[var][1]]
                    elif isinstance(delta[l.index(var)],list): 
                        if not 'mesh' in var:
                            new_val = [sum(x) for x in zip(starting_inputs[var][0], [d*(r+first-1)*(1+hint_) for d in delta[l.index(var)]])]
                            new_val = [new_val, starting_inputs[var][1]]
                        else:
                            new_val = [sum(x) for x in zip(starting_inputs[var], [d*(r+first-1)*(1+hint_) for d in delta[l.index(var)]])]
                    space[var].append(new_val)
                    #print(new_val)
            elif 'commensurate' in i.keys():
                for r in range(1,i['steps']*i['max_iterations']+1):
                    if r <= i['steps']*i['iter']: 
                        continue
                    if first == 0: first = 1
                    if 'mesh' in var:
                            new_val = [a*b for a,b in zip(starting_inputs[var], [delta[l.index(var)]*(r+first-1)*(1+hint_),
                                                                                 delta[l.index(var)]*(r+first-1)*(1+hint_),
                                                                                 delta[l.index(var)]*(r+first-1)*(1+hint_)])]
                    elif isinstance(starting_inputs[var][0],int) or isinstance(starting_inputs[var][0],float):
                        new_val = starting_inputs[var][0]*delta[l.index(var)]*(r+first-1)*(1+hint_)
                        if not 'mesh' in var:
                            new_val = [new_val, starting_inputs[var][1]]
                    elif isinstance(starting_inputs[var][0],list): 
                        if not 'mesh' in var:
                            new_val = [a*b for a,b in zip(starting_inputs[var][0], [d*(r+first-1)*(1+hint_) for d in delta[l.index(var)]])]
                            new_val = [new_val, starting_inputs[var][1]]
                        
                    space[var].append(new_val)
                    #print(new_val)
            else:
                for r in range(len(i['space'])):
                    new_val = i['space'][r][l.index(var)]
                
                    space[var].append(new_val)
            
            #for ii in range(len(space[var]),len(existing_inputs[var])-len(space[var])):
            #    space[var].append(existing_inputs[var][ii])


        first = 1

    existing_inputs.update(space)
    param_space = copy.deepcopy(existing_inputs)
    for v in l:
        for r in range(calc_dict['steps']*calc_dict['iter']):
            param_space[v].pop(0)
    

    return param_space, existing_inputs


def convergence_workflow_manager(parameters_space, wfl_settings, inputs, kpoints):

    workflow_dict = {}
    new_l = []

    #here should be a default list of convergence "parameters_space".
    if isinstance(parameters_space,list):
        parameters_space = List(list=parameters_space)
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
    workflow_dict['convergence_algorithm'] = copy_wfl_sett.pop('convergence_algorithm','dummy')
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
        for i in range(calc_manager['iter']*calc_manager['steps']-(oversteps)):
            for j in calc_manager['var']:
                workflow_dict['parameter_space'][j].pop(0)
    for i in none_encountered: 
            gs = workflow_dict['global_step'][workflow_dict['uuid']==i].index
            workflow_dict['workflow_story'].at[gs,'failed']=True
            workflow_dict['workflow_story'].at[gs,'useful']=False
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

def prepare_for_ce(workflow_dict={},keys=['gap_GG'],var_=[]):
    workflow_story = workflow_dict
    real = workflow_story[workflow_story.failed == False]
    lines = {}
    for k in ['BndsRnXp','GbndRnge','NGsBlkXp','kpoint_mesh']:
        if k in var_ and k in ['BndsRnXp','GbndRnge'] and not k == 'kpoint_mesh':
            lines[k] = np.array([i[0] for i in zip(list(real[k].values))])[:,1]
        elif k in var_ and k in ['kpoint_mesh']:
            lines[k] = np.array([i[0] for i in zip(list(real[k].values))])[:,0]
            for i in range(1,3):
                lines[k] *= np.array([i[0] for i in zip(list(real[k].values))])[:,i]
        elif k in var_:
            lines[k] = np.array([i for i in zip(list(real[k].values))])[:,0]
    homo = {}
    for key in keys:
        homo[key] = real[key].values
    
    return real,lines,homo


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
            
        return self.conv_array, self.delta, converged, is_converged, oversteps-1, converged_result
    
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
        extra, pcov = curve_fit(self.convergence_function,self.p,self.delta,p0=[1,1]*len(self.parameters))
        self.extra = extra
        print(extra)
        for i in range(len(self.parameters)):
            a = extra[2*i]
            b = extra[2*i+1]
            self.extrapolated = b*self.extrapolated
            f = lambda x: a/x**self.power_law[i]
            x_1 = a/self.thr
            x_2 = np.sqrt(abs(a)/self.thr)
            print(x_1,x_2)
            delta_ = self.p[i][-1] - self.p[i][-2]
            delta_1 = x_1 - self.p[i][-1]
            delta_2 = x_2 - self.p[i][-1]
            
            print(self.delta)
            print('error = ',a/(self.p[i][-1]))
            print('grad = ',a/(self.p[i][-1]**2))
            print('curv = ',2*a/(self.p[i][-1]**3))     
            
            alpha = delta_ #/ b
            beta = delta_**2 #/ b
            gamma = delta_**3 #/ b
            
            d = alpha*a/(self.p[i][-1])+beta*a/(self.p[i][-1]**2)+gamma*2*a/(self.p[i][-1]**3)
            
            print('alpha*error = ',alpha*a/(self.p[i][-1]))
            print('beta*grad = ',beta*a/(self.p[i][-1]**2))
            print('gamma*curv = ',gamma*2*a/(self.p[i][-1]**3)) 
            
            print('sum: ',delta_+abs(d))
            print('log(thr)*sum: ',abs(np.log10(self.thr))*(delta_+abs(d)))
            print(np.log10(self.thr))
            
            '''
            self.prediction = minimize(f,x0=self.p[i][-1],tol=0.1,method='BFGS')
            print(self.prediction,'\n')
            self.hint[self.parameters[i]] = int(self.prediction.x[0])
            f_2 = lambda x: -a/x**(1+self.power_law[i])*self.power_law[i]
            print('grad renorm:',self.p[i][-1]*f_2(self.p[i][-1]))
            print('delta hint:',abs(self.p[i][-1]*f_2(self.p[i][-1]))/self.thr,'\n') #ma é uguale a fun*100 ... ?
            '''
        
        hint = (delta_ + abs(np.log10(self.thr))*(delta_+abs(d)))/delta_ -1

        return hint

#@conversion_wrapper
def analysis_and_decision(calc_dict, workflow_dict):
    
    workflow_story = pd.DataFrame.from_dict(workflow_dict['workflow_story']) 
    steps = calc_dict['steps']*calc_dict['iter']+1

    if workflow_dict['type'] == '1D_convergence':
        '''documentation...'''
        window =  calc_dict['conv_window']
        tol = calc_dict['conv_thr']
        if isinstance(calc_dict['var'],list):
            var = calc_dict['var'][0]
        else:
            var = calc_dict['var']
        converged = True
        oversteps = 0
        oversteps_1 = 0
        none_encountered = list(workflow_story.uuid[workflow_story.failed == True])

        real,lines,homo = prepare_for_ce(workflow_dict=workflow_story,var_ = calc_dict['var'])
         
        y = Convergence_evaluator(conv_array=homo['gap_GG'][-steps:], thr=tol, window=window, parameters=[var], p=[lines[var][-steps:],])
        conv_array, delta, converged, is_converged, oversteps, converged_result = y.dummy_convergence() #just convergence as before


        if workflow_dict['convergence_algorithm'] != 'dummy':
            hint = y.convergence_prediction()
        else:
            hint = 0


        return is_converged, oversteps, none_encountered, homo, hint

    return is_converged, oversteps, none_encountered, hint    
    



###############################  parallelism  ####################################

def build_parallelism_instructions(instructions):

    instructions['automatic'] = instructions.pop('automatic', False)
    instructions['semi-automatic'] = instructions.pop('semi-automatic', False)
    instructions['manual'] = instructions.pop('manual', False)
    instructions['function'] = instructions.pop('function', False)

    return instructions