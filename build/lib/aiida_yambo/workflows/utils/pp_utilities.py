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
from aiida_yambo.utils.common_helpers import*

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

    return ef

def collect_results(node_pk):    #returns array (val_1,val_2....,result_eV_1,...) to be further analyzed 
        
        y = load_node(node_pk).outputs.story.get_list() 
        p = pd.DataFrame(y[1:][:],columns = y[0][:]) 
        rows = len(p) 
        cols = 0 
        len_val = 1 
        len_res = 1 
        last_c = get_called(node_pk,depth=3)
        ef = take_fermi(last_c.pk)
        print('Fermi Energy is {} eV'.format(ef))

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


def parse_data(wfl_pk, folder_name='', title='run'):

    if folder_name == '':
        folder_name = 'results_'+str(wfl_pk)
    print('the folder name will be: {}'.format(folder_name))
    k, p = collect_results(wfl_pk)
    
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


###### PLOT ######

def plot_1D_convergence(pk,title='',xlabel='step',ylabel='eV',where=1,physical_quantity='gap',\
              units={'NGsBlkXp':'Ry','kpoints':'density^-1'}, save = False):

    colors = list(matplotlib.colors.TABLEAU_COLORS.items())

    x = load_node(pk)
    y = x.outputs.story.get_list()

    for i in range(len(y)):
        string=''
        if isinstance(y[i][y[0].index('var')],list):
            print(y[i][y[0].index('var')])
            for k in y[i][y[0].index('var')]:
                string += k+' & '
            string= string+'qwerty'
            string = string.replace('& qwerty','')
            print(string)
            y[i][y[0].index('var')]=string

    tot = pd.DataFrame(y[1:],columns=y[0])
    conv = tot[tot['useful']==True]
    print(conv,tot)
    fig,ax = plt.subplots()
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid()

    ax.set_title(title)
    ax.plot(conv['global_step'],np.array(conv['result_eV'].to_list())[:,range(where)],'-',\
            label='convergence path')
    for j in range(where):
        ax.plot(tot['global_step'],np.array(tot['result_eV'].to_list())[:,j],'*--',
                color='black',label='full path - '+str(tot['where_in_words'].to_list()[0][j]))

    b=[]

    for i in conv['var']:
        if i not in b:
            try:
                unit = units[i]
            except:
                unit = ''
            color = colors[len(b)+where+1][0]
            act = conv[conv['var']==str(i)]['value'].to_list()
            print(act)
            for j in range(where):
                if j == 0:
                    label=str(i)+' - '+str(act[-1])+' '+str(unit)
                else:
                    label = None
                ax.plot(conv['global_step'],np.ma.masked_where(np.array(conv['var'].to_numpy()!=str(i)),\
                            np.array(conv['result_eV'].to_list())[:,j]),'o-' \
                        ,label=label)
            b.append(i)

    plt.legend()
    
    if save:
            fig.savefig(str(pk)+'conv.png')

def plot_2D_convergence(xdata, ydata, zdata, labels = {'x_label':'bands','y_label':'Ry','z_label': 'eV'}, title='Gap', plot_type='3D', save = False):      
        
    #matplotlib.rcParams['legend.fontsize'] = 10
    
    
    if plot_type=='3D':
        fig = plt.figure()
        ax = fig.gca(projection='3d')

        for i in np.unique(xdata):
            ind = np.where(xdata==i) 
            z = zdata[ind]
            x = xdata[ind]
            y = ydata[ind]
            ax.plot(x, y, z, '-o',label= '{} {}'.format(int(i), labels['x_label']))
    
        ax.set_title(title)
        ax.set_xlabel(labels['x_label'])
        ax.set_ylabel(labels['y_label'])
        ax.legend()
        plt.show()
        
        if save:
            fig.savefig(title+'3d.png')
    
    elif plot_type=='2D':
        fig, ax = plt.subplots()
        for i in np.unique(xdata):
            ind = np.where(xdata==i)    
            plt.plot(ydata[ind],zdata[ind],'-o',label='{} {}'.format(int(i),labels['x_label']))
        ax.set_title(title)
        ax.set_xlabel(labels['y_label'])
        ax.set_ylabel(labels['z_label'])
        ax.legend()
        plt.show()
        if save:
            fig.savefig(title+'2d_1.png')
        
        fig, ax = plt.subplots()
        for i in np.unique(ydata):
            ind = np.where(ydata==i)    
            plt.plot(xdata[ind],zdata[ind],'-o',label='{} {}'.format(int(i),labels['y_label']))
        ax.set_title(title)
        ax.set_xlabel(labels['x_label'])
        ax.set_ylabel(labels['z_label'])
        ax.legend()
        plt.show()
        if save:
            fig.savefig(title+'2d_2.png')