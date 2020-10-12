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
from aiida.orm.nodes.process.workflow.workchain import WorkChainNode


###### PLOT ######

def plot_1D_convergence(ax, history, title='',where=1,\
              units={'NGsBlkXp':'(Ry)','kpoints':' (mesh)'}):

    colors = list(matplotlib.colors.TABLEAU_COLORS.items())
    
    if isinstance(history,WorkChainNode):
        y = history.outputs.history.get_dict() 
        history= pd.DataFrame(y)
    elif isinstance(history,int) or isinstance(history,str):
        x = load_node(history)
        y = x.outputs.history.get_dict() 
        history= pd.DataFrame(y)     
    elif isinstance(history,dict):
        y = history
        history= pd.DataFrame(y)
    elif 'DataFrame' in str(type(history)):
        pass
    else:
        raise TypeError('You have to provide: node, node_pk, output_dict or dataframe')      
    
    yy = list(history.keys())
    y = history.values.tolist()
    y.insert(0, yy)
    
    for i in range(len(y)):
        string=''
        if isinstance(y[i][y[0].index('var')],list):
            #print(y[i][y[0].index('var')])
            for k in y[i][y[0].index('var')]:
                string += k+' & '
                string= string+'qwerty'
                string = string.replace('& qwerty','')
                #print(string)
                y[i][y[0].index('var')]=string
        tot = pd.DataFrame(y[1:],columns=y[0])  
                
    conv = tot[tot['useful']==True]
    #print(conv,tot)

    ax.plot(conv['global_step'],np.array(conv['result_eV'].to_list())[:,range(where)],'-',\
            label='convergence path')
    for j in range(where):
        ax.plot(tot['global_step'],np.array(tot['result_eV'].to_list())[:,j],'*--',
                color='black',label='full path')

    b=[]

    for i in conv['var']:
        if i not in b:
            try:
                unit = units[i]
            except:
                unit = ''
            color = colors[len(b)+where+1][0]
            val = conv[conv['var']==str(i)]['value'].values[-1]
            #print(act)
            for j in range(where):
                if j == 0:
                    if i == 'kpoints':
                        try:
                            val = find_pw_parent(load_node(int(conv[conv['var']==str(i)]['calc_pk'].values[-1]))).inputs.kpoints.get_kpoints_mesh()[0]
                            label=str(i)+' - '+str(val)+' '+str(unit)
                        except:
                            label=str(i)+' - '+str(val)+' '+str(unit)
                    else:
                        label=str(i)+' - '+str(val)+' '+str(unit)
                else:
                    label = None
                ax.plot(conv['global_step'],np.ma.masked_where(np.array(conv['var'].to_numpy()!=str(i)),\
                            np.array(conv['result_eV'].to_list())[:,j]),'o-' \
                        ,label=label)
            b.append(i)

def plot_2D_convergence(ax, xdata=None, ydata=None, zdata=None, parameters = {'x':'bands','y':'G-vecs (Ry)'}, plot_type='3D'):      

    if not isinstance(xdata, np.ndarray):
        raise TypeError('xdata has to be numpy.ndarray')
    if not isinstance(ydata, np.ndarray):
        raise TypeError('ydata has to be numpy.ndarray')
    if not isinstance(zdata, np.ndarray):
        raise TypeError('zdata has to be numpy.ndarray')
    
    if plot_type=='3D':

        for i in np.unique(xdata):
            ind = np.where(xdata==i) 
            z = zdata[ind]
            x = xdata[ind]
            y = ydata[ind]
            ax.plot(x, y, z, '-o',label= '{} {}'.format(int(i), parameters['x']))
    
    elif plot_type=='2D':
        
        #here, you have to change the order to have the two diff vars...
        for i in np.unique(xdata):
            ind = np.where(xdata==i)    
            ax.plot(ydata[ind],zdata[ind],'-o',label='{} {}'.format(int(i),parameters['x']))
