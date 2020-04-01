#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from aiida.orm import load_node

def plot_conv(pk,title='',xlabel='step',ylabel='eV',where=1,physical_quantity='gap',\
              units={'NGsBlkXp':'Ry','kpoints':'density^-1'}):

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


def collect_results(node_pk):    #returns array (val_1,val_2....,result_eV_1,...) to be further analyzed 
        
        y = load_node(node_pk).outputs.story.get_list() 
        p = pd.DataFrame(y[1:][:],columns = y[0][:]) 
        rows = len(p) 
        cols = 0 
        len_val = 1 
        len_res = 1 
        last_c = get_called(wfl_pk,depth=3)
        ef = take_fermi(last_c.pk)
        print('Fermi Energy is {} eV'.format(ef))

        if isinstance(p['value'].iloc[1],list): 
            len_val = len(p['value'].iloc[1]) 
            cols = cols + len(p['value'].iloc[1]) 
        else: 
            cols = cols+1 
      
        if isinstance(p['result_eV'].iloc[1],list): 
            len_res = len(p['result_eV'].iloc[1]) 
                cols = cols + len(p['result_eV'].iloc[1]) 
        else: 
            cols = cols+1    

        print('varibles are {}'.format(p['var'].iloc[0]))    

        k = np.zeros((rows,cols)) 
        for i in range(rows): 
            for j in range(len_val): 
                if isinstance(p['value'].iloc[i][j],list): 
                    k[i,j] = p['value'].iloc[i][j][-1]-p['value'].iloc[i][j][0]+1 
                else: 
                    k[i,j] = p['value'].iloc[i][j] 
            for l in range(len_res): 
                k[i,l+len_val] = p['result_eV'].iloc[i][l]+ef
        return k

def plot_2d_results(node,lab = '',title=''):      #just a 3d plot
    y = load_node(node).outputs.story.get_list()
    p = pd.DataFrame(y[1:][:],columns = y[0][:])
    k = np.zeros((len(p),3)) ;
    for i in range(len(p)):
         if isinstance(p['value'].iloc[i][0],list):
            k[i,0] = p['value'].iloc[i][0][1]
            k[i,1] = p['value'].iloc[i][1][1]
            k[i,2] = p['result_eV'].iloc[i][0]
         else:
            k[i,0] = p['value'].iloc[i][0]
            k[i,1] = p['value'].iloc[i][1]
            k[i,2] = p['result_eV'].iloc[i][0]

    matplotlib.rcParams['legend.fontsize'] = 10
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    ax.set_title(title)
    z = k[:,2]
    x = k[:,0]
    y = k[:,1]
    ax.plot(x, y, z, '-o',label=lab)
    ax.set_xlabel(p['var'].iloc[1][0])
    ax.set_ylabel(p['var'].iloc[1][1])
    ax.legend()
    plt.show()

def take_fermi(calc_node_pk):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    node = load_node(calc_node_pk)
    path_folder = node.outputs.retrieved._repository._repo_folder.abspath+'/path/'
    for i in os.listdir(path_folder):
        if 'r-aiida.out' in i:
            file = open(path_folder+i,'r')
    for line in file:
        if '[X]Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[3]))
            ef = line.split()[3]

    return ef