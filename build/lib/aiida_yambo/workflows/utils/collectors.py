#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import shutil
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from aiida.orm import load_node
from aiida_yambo.utils.common_helpers import *
from aiida_yambo.parsers.utils import *
from aiida.orm.nodes.process.workflow.workchain import WorkChainNode

def take_fermi(calc_node_pk):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    node = load_node(calc_node_pk)
    path_folder = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
    for i in os.listdir(path_folder):
        if 'r-aiida.out' in i:
            file = open(path_folder+i,'r')
    for line in file:
        if '[X]Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[3]))
            ef = float(line.split()[3])
        if '[X] Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[4]))
            ef = float(line.split()[4])

    return ef

def collect_all_params(story, param_list=['BndsRnXp','GbndRnge','NGsBlkXp']):
    
    if isinstance(story,WorkChainNode):
        y = story.outputs.story.get_dict() 
        df= pd.DataFrame(y)
    elif isinstance(story,int):
        x = load_node(story)
        y = x.outputs.story.get_dict() 
        df= pd.DataFrame(y)
    elif isinstance(story,dict):
        df= pd.DataFrame(story)
    elif 'DataFrame' in str(type(story)):
        df=story
    else:
        raise TypeError('You have to provide: node, node_pk, output_dict or dataframe')  
    
    list_for_df=[]
    for calc in df['calc_pk']:
        node = load_node(int(calc))
        node_pw = find_pw_parent(node, calc_type=['nscf','scf'])
        mesh = node_pw.inputs.kpoints.get_kpoints_mesh()[0]
        distance_mesh = get_distance_from_kmesh(node_pw)
        list_for_df.append([node.inputs.parameters.get_dict()[j] for j in param_list]+\
              [mesh]+[distance_mesh]+df[df['calc_pk']==calc]['result_eV'].values.tolist()\
                           +[df[df['calc_pk']==calc]['useful'].values])
        df_c=pd.DataFrame(list_for_df,columns=param_list+['mesh','distance_mesh']+['result_eV','useful'])
    
    return df_c

def collect_2D_results(story=None, last_c=None, ef = 0):    #returns array (val_1,val_2....,result_eV_1,...) and pandas DF to be further analyzed 
        
    if isinstance(story,WorkChainNode):
        y = story.outputs.story.get_dict() 
        story=pd.DataFrame(y)
    elif isinstance(story,int):
        x = load_node(story)
        y = x.outputs.story.get_dict() 
        story=pd.DataFrame(y)    
    elif isinstance(story,dict):
        story=pd.DataFrame(story)
    elif 'DataFrame' in str(type(story)):
        pass
    else:
        raise TypeError('You have to provide: node, node_pk, output_dict or dataframe')    
    
    yy = list(story.keys())
    y = story.values.tolist()
    y.insert(0, yy)
    
    p = pd.DataFrame(y[1:],columns=y[0])

    rows = len(p) 
    cols = 0 
    len_val = 1 
    len_res = 1 
    
    if last_c:
        ef = take_fermi(last_c.pk)
        print('Fermi Energy is {} eV'.format(ef))
    else:
        print('setting Fermi Energy to zero eV, if you need Ef just provide last_c=<pk_calc> as input') 

    if isinstance(p['value'].iloc[0],list): 
        len_val = len(p['value'].iloc[0]) 
        cols = cols + len(p['value'].iloc[0]) 
    else: 
        cols = cols+1 
    
    if isinstance(p['result_eV'].iloc[0],list): 
        len_res = len(p['result_eV'].iloc[0]) 
        cols = cols + len(p['result_eV'].iloc[0]) 
    else: 
        cols = cols+1    

    print('variables are {}'.format(p['var'].iloc[0]))    

    k = np.zeros((rows,cols)) 
    for i in range(rows): 
        for j in range(len_val): 
            if isinstance(p['value'].iloc[i][j],list): 
                k[i,j] = p['value'].iloc[i][j][-1]-p['value'].iloc[i][j][0]+1 
            else: 
                k[i,j] = p['value'].iloc[i][j] 
        for l in range(len_res):
            if p['result_eV'].iloc[i][l] == 0:
                pass
            else:
                k[i,l+len_val] = p['result_eV'].iloc[i][l]+ef
    return k, p


def parse_2D_data(wfl_pk, folder_name='', title='run', last_c_ok_pk=None):

    if folder_name == '':
        folder_name = 'results_'+str(wfl_pk)
    print('the folder name will be: {}'.format(folder_name))
    
    k, p = collect_results(wfl_pk, last_c=last_c_ok_pk)
    
    if not folder_name in os.listdir():
        os.mkdir(folder_name)
        os.mkdir(folder_name+'/DATA/')
        os.mkdir(folder_name+'/DATA/LOG/')
    for i in range(len(k)):
        try:
            print(int(p['calc_pk'].iloc[i]))
            repo = load_node(int(p['calc_pk'].iloc[i])).outputs.retrieved._repository._repo_folder.abspath
            repo +='/path/'
            title = ''
            for j in range(len((p['var'].iloc[0]))):
                title += '_'+str(int(k[i,j]))
            print('the title will be: \n {}'.format(title))
            if not load_node(int(p['calc_pk'].iloc[i])).is_finished_ok:
                title += 'failed'
            for file in os.listdir(repo):
                print(file)
                if 'o-' in file:
                    shutil.copyfile(repo+file,folder_name+'/DATA/o-'+title+'.qp_'+str(int(p['calc_pk'].iloc[i])))
                elif 'l-' in file:
                    shutil.copyfile(repo+file,folder_name+'/DATA/LOG/'+'l-'+title+'_CPU_'+str(int(p['calc_pk'].iloc[i])))
                elif 'r-' in file and not 'er-' in file:
                    shutil.copyfile(repo+file,folder_name+'/DATA/r-'+title+'_'+str(int(p['calc_pk'].iloc[i]))) 
                    np.set_printoptions(suppress=True)
        except:
            pass
       
    tot=''
    try:
        with open(folder_name+'/results.txt', 'r+') as resume:
            for line in resume.readlines():
                tot += line 
                tot += '\n'
    except:
        print('not file with results found, creating....')
        
        
    print('tot is {}'.format(tot))       
    with open(folder_name+'/results.txt', 'a+') as resume:
        for i in range(len(k)):
            can_write= False
            res = str(k[i,:]).replace('[','').replace(']','')
            print('can I write {} ? '.format(res))
            if res.split()[-1] != '0.':
                print('can')
                can_write = True
            else:
                print('cannot_ wrong')
                can_write = False
            if res+'\n' in tot:
                print('cannot')
                can_write = False
            if can_write:
                print('can write')
                print(str(res.split()[-1]))
                resume.write(res)
                resume.write('\n')
    
            
    return k


def get_timings(story):

    if isinstance(story,WorkChainNode):
        y = story.outputs.story.get_list() 
    elif isinstance(story,int):
        x = load_node(story)
        y = x.outputs.story.get_list()      
    elif isinstance(story,list):
        y = story
    elif 'DataFrame' in str(type(story)):
        yy = list(story.keys())
        y = story.values.tolist()
        y.insert(0, yy)
    else:
        raise TypeError('You have to provide: node, node_pk, output_list or dataframe')    

    df = pd.DataFrame(y[1:],columns=y[0])

    timings = []
    for calc_pk in df.calc_pk:
        ywfl = load_node(int(calc_pk)).caller.caller
        
        condition = df.calc_pk == calc_pk
        time_gw=0
        time_pw=0
        for called in ywfl.called_descendants:

            pt=called.process_type
            
            if 'aiida.calculations' in pt and 'yambo' in pt:

                time_gw += load_node(int(called.pk)).outputs.output_parameters.get_dict()['last_time']
    
            elif 'aiida.calculations' in pt and 'pw' in pt:
            
                if df['var'][condition].values[0] == 'kpoints' or df['global_step'][condition].values[0] == 1:
                    str_t = load_node(int(called.pk)).outputs.output_parameters.get_dict()['wall_time'].replace('h','h-').replace('m','m-').replace('s','l')
                    time_pw += yambotiming_to_seconds(str_t)
            
        timings.append([df.global_step[condition].values[0],df['var'][condition].values[0],time_gw,time_pw])
    df_t = pd.DataFrame(timings, columns =['step','var','time_gw','time_pw'])
    return df_t