from __future__ import absolute_import

import numpy as np
from scipy import optimize
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
from aiida_yambo.utils.common_helpers import *


def create_grid_1D(edges=[],delta=[],alpha=1/3,add = [],var=['BndsRnXp',],shift=0):
    
    if var[0] == 'kpoint_mesh':
        b_min = edges[0]
        b_max = edges[1]

        for i in range(3):
            b_min[i] += shift*delta[i]
            b_max[i] += shift*delta[i]

        A = b_min
        B = b_max
        E = []
        F = []
        for i in range(3):
            E.append(alpha*(b_max[i]-b_min[i])+b_min[i])
            F.append((1-alpha)*(b_max[i]-b_min[i])+b_min[i])

            if delta[i] == 0: 
                space_b = np.array([A[-1]])
            else:
                space_b = np.arange(b_min[i], b_max[i]+1,delta[i])

            E[i] = space_b[abs(space_b-E[i]).argmin()]
            F[i] = space_b[abs(space_b-F[i]).argmin()]

        b = []

        for i in [A,E,F,B]:
            b.append(i)

        for i in add:
            if add != []:
                b.append(i)

        return {'kpoint_mesh':b} #A,B,C,D,E,F

    else:
        b_min = edges[0]+shift[0]*delta[0]
        b_max = edges[1]+shift[0]*delta[0]

        A = b_min
        B = b_max

        E = alpha*(b_max-b_min)+b_min
        F = (1-alpha)*(b_max-b_min)+b_min

        space_b = np.arange(b_min, b_max+1,delta[0])

        E = space_b[abs(space_b-E).argmin()]
        F = space_b[abs(space_b-F).argmin()]

        b = []

        for i in [A,E,F,B]:
            b.append(i)

        for i,j in add:
            b.append(i)

        return {var[0]:b} #A,B,C,D,E,F

class The_Predictor_1D():
    
    '''Class to analyse the convergence behaviour of a system
    using the new algorithm.'''
    
    def __init__(self, **kwargs):
            
        for k,v in kwargs['calc_dict'].items():
            setattr(self,k,copy.deepcopy(v))
        for k,v in kwargs.items():
            if k != 'calc_dict': setattr(self,k,copy.deepcopy(v))
        #print(kwargs['calc_dict'])
        
        if isinstance(self.what,list):
            self.what = self.k
        
        if not hasattr(self,'Fermi'): self.Fermi=0

        self.var_ = copy.deepcopy(self.var) #to delete one of the band var:
        self.delta_ = copy.deepcopy(self.delta) #to delete one of the band var:
        self.index = [0] 

        if 'BndsRnXp' in self.var and 'GbndRnge' in self.var:
            self.var_.remove('GbndRnge')
            self.delta_.pop(self.var.index('GbndRnge'))

        #print('var',self.var)
        #print('var_',self.var_)

        for i in self.var_:
            setattr(self,i,copy.deepcopy(list(self.result[i].values)))
        
        
        self.parameters = np.array(self.grid[self.var_[0]]) #per i k, griglia specifica da inputs.
        #ci vuole un k adapter
        if 'kpoint_mesh' in self.var_:
            
            self.parameters = self.grid['mesh'] #per i k, griglia specifica da inputs.

            kx = []
            k3 = []
            for i in self.result['kpoint_mesh']:
                kx.append(i[0])
                k3.append(i[0]*i[1]*i[2])
            
            k_true=[]
            for i in self.result['uuid']:
                k_true.append(find_pw_parent(load_node(i)).outputs.output_parameters.get_dict()['number_of_k_points'])

            self.result['kx'] = kx
            self.result['k^3'] = k3
            self.result['nk'] = k_true
            
            
            self.starting_mesh = self.parameters[0]
            self.parameters = np.array(self.parameters)
            self.p = self.parameters
            self.parameters = self.parameters[:,0]*self.parameters[:,1]*self.parameters[:,2]
            self.delta_z = max(1,self.delta_[2])
            self.delta_y = max(1,self.delta_[1])
            self.delta_x = max(1,self.delta_[0])
            self.delta_ = self.delta_x*self.delta_y*self.delta_z

        #self.bb, self.GG = copy.deepcopy(list(self.result.BndsRnXp.values)),copy.deepcopy(list(self.result.NGsBlkXp.values))
        
        self.res = copy.deepcopy(self.result[self.what].values[:] + self.Fermi)
        
        try:
            self.bb_Ry = copy.deepcopy(self.bande[0,np.array(self.result.BndsRnXp.values)-1]/13.6)
        except:
            self.bb_Ry = copy.deepcopy(self.bande[0,-1]/13.6)
            
        self.r[:] = self.r[:] + self.Fermi
        
        #self.G = copy.deepcopy(self.G)
        
        #print('Params',self.parameters)
        
    
    def addplot_info_1D(self,fig,ax,
                               x,y,
                               marker='s',
                               lw = 7,
                               label='',
                               just_points=False):       
        
        if not just_points:
            ax.legend(fontsize=13)
            dictionary_labels = {}

            ax.set_xlabel(self.var[0],fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            ax.grid()

            try:
                if 'BndsRnXp' in self.var or 'GbndRnge' in self.var:
                    l_ = list(set(self.result.BndsRnXp.values))
                    l_.sort()
                    #l__ = list(set(result.BndsRnXp.values))
                    l__ = list(set(np.round(self.bb_Ry,0)))
                    l__.sort()
                    ax2 = ax.twiny()
                    ax2.set_xticks(l_[::3])
                    ax2.set_xbound(ax.get_xbound())
                    ax2.set_xticklabels(l__[::3],fontdict={'size':20})
                    ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})
            except:
                pass
            
################################################################

    def fit_space_1D(self,fit=False,alpha=1,beta=1,reference = None,verbose=True,plot=False,dim=100,b=None,g=None,save=False):
        
        f = lambda x,a,b: (a/x**alpha + b)
        fx = lambda x,a: -alpha*a/(x**(alpha+1))
         
        xdata,ydata = self.parameters,self.r
        #print('fitting all simulations.')

        popt,pcov = curve_fit(f,xdata=xdata,
                      ydata=ydata,sigma=1/xdata,
                      bounds=([-np.inf,-np.inf],[np.inf,np.inf]))
        
        MAE_int = np.average((abs(f(xdata,popt[0],popt[1])-ydata)),weights=xdata)
        print('MAE fit = {} eV; power law = {}'.format(MAE_int,alpha))
        self.MAE_fit = MAE_int
        
        if verbose: 
            print(np.max(xdata)*10)
            print(np.min(xdata))
            print('conv_thr, ',self.conv_thr)
            
        ###########Preliminary fit#################################
        
        self.X_fit = np.arange(np.min(xdata),np.max(xdata)*10,self.delta_) 
        
        if self.var_[0] == 'kpoint_mesh':
            l = [1,2,3]
            for i in range(3):
                if self.delta[i] != 0:
                    l[i] = np.arange(np.min(self.p[:,i]),np.max(self.p[:,i])*10,self.delta[i])
                    length = len(l[i])
                else:
                    l[i] = 0 
            for i in range(3):
                if self.delta[i] == 0:
                    l[i] = np.ones(length)
            
            #print('AAAAAAA',length, l)
            self.kx_fit = l[0]
            self.ky_fit = l[1]
            self.kz_fit = l[2]

            l_min = min(len(l[0]),len(l[1]),len(l[2])) #this is needed to match if some kx,ky,kz created with np.arange have different lengths
            self.kx_fit = l[0][:l_min]
            self.ky_fit = l[1][:l_min]
            self.kz_fit = l[2][:l_min]

            self.X_fit = l[0][:l_min]*l[1][:l_min]*l[2][:l_min]
        
        self.Zx_fit = fx(self.X_fit,popt[0])
        
        self.extra = popt[1]

        ###########Estimation of the plateaux corner###############
        
        if reference == 'extra':
            reference = self.extra
        else:
            self.Z_fit = f(self.X_fit,popt[0],popt[1])  
            reference = self.Z_fit[-1]
            
        if self.conv_thr_units=='%':
            thr = self.conv_thr*abs(reference)/100
        else:
            thr = self.conv_thr
            
        
        self.condition_conv_calc = np.where(abs(self.Zx_fit)<5e-5)
        
        if len(self.X_fit[self.condition_conv_calc]) == 0 : return False
        if not b: b = max(max(xdata),self.X_fit[self.condition_conv_calc][0])
            
        #print('b: {}\ng: {}'.format(b,g))
        
        p = f(max(xdata),popt[0],popt[1])
        p_H = f(b,popt[0],popt[1])
        try:
            l = ydata[np.where(xdata == max(xdata))][0]
        except:
            l = ydata[-1]
        
        print('extra={} eV, \nlast calculation={} eV \nlast calculation from fit={} eV'.format(round(popt[1],3),
                                                                                          round(l,2),round(p,3)))
        
        if verbose: print('{} highest point from fit = {} eV\n'.format(b,round(p_H,3)))
        if verbose: print('\nrelative err extra - last calculation = {}%'.format(round(100*abs((popt[1]-l)/(l)),3)))      
        if verbose: print('relative err extra - highest point from fit = {}%'.format(round(100*abs((popt[1]-p_H)/(p_H)),3)))
        
        if self.var_[0] == 'kpoint_mesh':
            self.kx_fit = self.kx_fit[self.X_fit <= max(max(xdata),self.X_fit[self.condition_conv_calc][0]*1.5)]
            self.ky_fit = self.ky_fit[self.X_fit <= max(max(xdata),self.X_fit[self.condition_conv_calc][0]*1.5)]
            self.kz_fit = self.kz_fit[self.X_fit <= max(max(xdata),self.X_fit[self.condition_conv_calc][0]*1.5)]
            self.X_fit = self.X_fit[self.X_fit <= max(max(xdata),self.X_fit[self.condition_conv_calc][0]*1.5)]
        else:
            self.X_fit = np.arange(min(xdata),b+1,self.delta_)
        
    
        
        self.Z_fit = f(self.X_fit,popt[0],popt[1])
        
        self.Zx_fit = fx(self.X_fit,popt[0])
        
        if plot:
            lw=3
            print('res min {}, res max {}'.format(min(self.res),max(self.res)))
            fig,ax = plt.subplots(figsize=[8,8])
            
            ax.plot(self.X_fit,self.Z_fit,
                    '-o',lw = lw,ms = 8,color='blue')

            ax.plot(xdata,ydata,
                    marker='o',ms=8,lw=0,color='black',label='simulations')
            
            ax.legend()
                        
            if save : plt.savefig('plot_fit_1D.png')

            
        return True
    

    def determine_next_calculation(self,
                                   overconverged_values=[],
                                   plot=False,
                                   reference = None,save=False,):
        
        print('last point:{} eV'.format(self.Z_fit[-1]))
        
        if reference == 'extra':
            reference = self.extra
        else:
            reference = self.Z_fit[-1]
            
        if self.conv_thr_units=='%':
            thr = self.conv_thr*abs(reference)/100
        else:
            thr = self.conv_thr
        
        #print(thr)
        discrepancy = np.round(abs(reference-self.Z_fit),abs(int(np.round(np.log10(1%thr),0))))
        condition = np.where((discrepancy<=thr))
        
        #print(condition)
        #print(self.Z_fit[condition])
        #print('\n')
        
        #print('Min G condition')
        #print(self.Z_fit[condition][0])
        #print(self.X_fit[condition][0])
        
        self.condition = condition
         
        conv_bands = self.X_fit[condition][0]
        conv_z = self.Z_fit[condition][0]
        
        self.next_step = {
            self.var_[0]:conv_bands,
            self.what: conv_z,
            'already_computed': False,
        }
        
        if conv_bands in self.parameters:
            self.next_step['already_computed'] = True

        if 'BndsRnXp' in self.var and 'GbndRnge' in self.var:
            self.next_step['GbndRnge'] = copy.deepcopy(self.next_step['BndsRnXp'])
        
        if plot:
            lw = 3
            fig,ax = plt.subplots(figsize=[8,8])
            
            ax.plot(self.X_fit,self.Z_fit,
                    '-o',lw = lw,ms = 8,color='grey',label='excluded points')
            
            ax.plot(self.X_fit[condition], self.Z_fit[condition],
                                      marker='o',lw = lw,ms=8,
                                      label='converged points',)
            
            ax.plot(self.parameters,self.r,
                    marker='o',ms=8,lw=0,color='black',label='simulations')
            
            
            ax.plot(conv_bands, conv_z,'red',
                                      marker='o',ms=8,lw=0,
                                      label='converged guess',
                   )   
            
            ax.legend()
            
            if save : plt.savefig('plot_next_1D.png')
        
        if self.var_[0] == 'kpoint_mesh':
            kx = self.kx_fit[self.X_fit==conv_bands]
            factor = (kx-self.starting_mesh[0])/self.delta[0]
            ky = factor*self.delta[1] + self.starting_mesh[1]
            kz = factor*self.delta[2] + self.starting_mesh[2]
        
        self.next_step[self.var_[0]] = [int(kx),int(ky),int(kz)]
        
        for k in range(3):
            if self.next_step[self.var_[0]][k] > self.max[k]:
                self.next_step['new_grid'] = True
                break
            
        print('guessed next step: {} \n\n\n'.format(self.next_step))

        return self.next_step
    
    def check_the_point(self,old_hints={}):
        
        if self.var_[0] == 'kpoint_mesh':
            self.old_discrepancy = \
            abs(old_hints[self.what] - self.result[(self.result['kx']==old_hints['kpoint_mesh'][0])][self.what].values[0])
            self.index = [int(self.result[(self.result['kx']==old_hints['kpoint_mesh'][0])].index.values[0])]


            print('Discrepancy with old prediction: {} eV'.format(self.old_discrepancy))

            if old_hints['kpoint_mesh'][0] == self.next_step[self.var_[0]][0]:
                self.point_reached = True
            else:
                self.point_reached = False
                print('new point predicted.')
            
        else:
            self.old_discrepancy = \
            abs(old_hints[self.what] - self.result[(self.result[self.var_[0]]==old_hints[self.var_[0]])][self.what].values[0])
            self.index = [int(self.result[(self.result[self.var_[0]]==old_hints[self.var_[0]])].index.values[0])]

            print('Discrepancy with old prediction: {} eV'.format(self.old_discrepancy))

            if old_hints[self.var_[0]] == self.next_step[self.var_[0]]:
                self.point_reached = True
            else:
                self.point_reached = False
                print('new point predicted.')
              
        return
    
    
    def analyse(self,old_hints={},reference = None, plot= False,save_fit=False,save_next = False,colormap='viridis'):
        
        self.check_passed = True
        error = 10
        power_laws = [1,2]
        
        if 'kpoint_mesh' in self.var_: power_laws = [0.5,1,2]

        for i in power_laws:
                self.check_passed = self.fit_space_1D(fit=True,alpha=i,beta=1,plot=False,dim=10,)
                if self.MAE_fit<error: 
                    ii = i
                    error = self.MAE_fit

        print('Best power law: {}'.format(i))  
        
        self.check_passed = self.fit_space_1D(fit=True,alpha=ii,beta=1,verbose=True,plot=plot,save=save_fit)
        
        if not self.check_passed:
            self.point_reached = False
            self.next_step = {'new_grid':True}
            return
        else:
            self.determine_next_calculation(plot=plot, save=save_next,reference=reference)
        
        if 'new_grid' in self.next_step.keys():
            if self.next_step['new_grid']: 
                self.check_passed = False
                self.point_reached = False
                return
            
        self.point_reached = False
        
        if reference == 'extra':
            reference = self.extra
        else:
            reference = self.Z_fit[-1]
            
        if self.conv_thr_units=='%':
            factor = 100/abs(reference)
        else:
            factor=1

        if old_hints or self.next_step['already_computed']:
                if self.next_step['already_computed']: 
                    old_hints = self.next_step
                    self.point_reached = True
                    
                self.check_the_point(old_hints)
                if reference == 'extra':
                    reference = self.extra
                else:
                    reference = self.Z_fit[-1]
                
                if np.round(abs(self.old_discrepancy),abs(int(np.round(np.log10(1%(self.conv_thr/factor)),0)))) <= self.conv_thr/factor: 
                    self.check_passed = True
                else:
                    self.check_passed = False

        if not self.check_passed and self.point_reached:
            self.next_step['new_grid'] = True
        elif self.MAE_fit > 10*self.conv_thr*factor:
            self.next_step['new_grid'] = True
        else:
            self.next_step['new_grid'] = False

        return True