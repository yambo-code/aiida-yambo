from __future__ import absolute_import

import numpy as np
from scipy import optimize
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
from aiida_yambo.utils.common_helpers import *


def create_grid(edges=[],delta=[],alpha=0.25,add = [[],[]],var=['BndsRnXp','NGsBlkXp'],shift=[0,0]):
    
    b_min = edges[0]+shift[0]*delta[0]
    b_max = edges[2]+shift[0]*delta[0]
    g_min = edges[1]+shift[1]*delta[1]
    g_max = edges[3]+shift[1]*delta[1]
    
    A = [b_min,g_min]
    B = [b_max,g_min]
    C = [b_max,g_max]
    D = [b_min,g_max]
    E = [alpha*(b_max-b_min)+b_min,(1-alpha)*(g_max-g_min)+g_min]
    F = [(1-alpha)*(b_max-b_min)+b_min,alpha*(g_max-g_min)+g_min]
    
    space_b = np.arange(b_min, b_max+1,delta[0])
    space_g = np.arange(g_min, g_max+1,delta[1])
    
    E[0] = space_b[abs(space_b-E[0]).argmin()]
    F[0] = space_b[abs(space_b-F[0]).argmin()]
    
    E[1] = space_g[abs(space_g-E[1]).argmin()]
    F[1] = space_g[abs(space_g-F[1]).argmin()]
    
    b = []
    G = []
    
    for i in [A,B,C,D,E,F]:
        b.append(i[0])
        G.append(i[1])
    
    for i,j in list(zip(add[0],add[1])):
        b.append(i)
        G.append(j)
    
    return {var[0]:b,var[1]:G} #A,B,C,D,E,F

class The_Predictor_2D():
    
    '''Class to analyse the convergence behaviour of a system
    using the new algorithm.'''
    
    def __init__(self, **kwargs):
            
        for k,v in kwargs['calc_dict'].items():
            setattr(self,k,copy.deepcopy(v))
        for k,v in kwargs.items():
            if k != 'calc_dict': setattr(self,k,copy.deepcopy(v))
        #print(kwargs['calc_dict'])
        
        if isinstance(self.what,list):
            self.what = self.what[0]
        
        if not hasattr(self,'Fermi'): self.Fermi=0

        self.var_ = copy.deepcopy(self.var) #to delete one of the band var:
        self.delta_ = copy.deepcopy(self.delta) #to delete one of the band var:
        self.index = [0] 

        if 'BndsRnXp' in self.var and 'GbndRnge' in self.var and len(self.var) > 2:
            self.var_.remove('GbndRnge')
            self.delta_.pop(self.var.index('GbndRnge'))

        print('var',self.var)
        print('var_',self.var_)

        for i in self.var_:
            setattr(self,i,copy.deepcopy(list(self.result[i].values)))
        
        self.parameters = np.array(list(self.grid.values()))
        
        #self.bb, self.GG = copy.deepcopy(list(self.result.BndsRnXp.values)),copy.deepcopy(list(self.result.NGsBlkXp.values))
        
        self.res = copy.deepcopy(self.result[self.what].values[:] + self.Fermi)
        
        try:
            self.bb_Ry = copy.deepcopy(self.bande[0,np.array(self.result.BndsRnXp.values)-1]/13.6)
        except:
            self.bb_Ry = copy.deepcopy(self.bande[0,-1]/13.6)
            
        self.r[:] = self.r[:] + self.Fermi
        
        #self.G = copy.deepcopy(self.G)
        
        print('Params',self.parameters)
        
    
    def plot_scatter_contour_2D(self,fig,ax,
                               x,y,z,
                               vmin,vmax,
                               colormap='gist_rainbow_r',
                               marker='s',
                               lw = 7,
                               label='',
                               just_points=False,bar=False):       
        
        #fig,ax = plt.subplots(figsize=[7,7])

        scatter = ax.scatter(x, y, 100, 
                             c=z,
                             marker=marker,
                             linewidth = lw,
                             label=label,
                             vmin=vmin,vmax=vmax,
                             cmap=colormap)
        
        if not just_points:
            ax.legend(fontsize=13)
            dictionary_labels = {}

            ax.set_xlabel('# of bands',fontdict={'fontsize':20})
            ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            ax.grid()

            try:
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
        
        if bar:
                cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
                cmap.set_label('eV', rotation=0,labelpad=20,fontsize=20)
                cmap.ax.tick_params(labelsize=20)
            
################################################################

    def fit_space_2D(self,fit=False,alpha=1,beta=1,reference = None,verbose=True,plot=False,dim=100,colormap='gist_rainbow_r',b=None,g=None,save=False):
        
        f = lambda x,a,b,c,d: (a/x[0]**alpha + b)*( c/x[1]**beta + d)
        fx = lambda x,a,c,d: -alpha*a/(x[0]**(alpha+1))*( c/x[1] + d)
        fy = lambda x,a,b,c: (a/x[0] + b)*( -beta*c/x[1]**(beta+1) )
        
        fxy = lambda x,a,c: -alpha*a/(x[0]**(alpha+1))*( -beta*c/x[1]**(beta+1))
         
        xdata,ydata = np.array((self.parameters[0,:],self.parameters[1,:])),self.r[:]
        print('fitting all simulations.')
        
        print(np.shape(1/(xdata[0]*xdata[1])))
            
        popt,pcov = curve_fit(f,xdata=xdata,
                      ydata=ydata,sigma=1/(xdata[0]*xdata[1]),
                      bounds=([-np.inf,-np.inf,-np.inf,-np.inf],[np.inf,np.inf,np.inf,np.inf]))
        
        MAE_int = np.average((abs(f(xdata,popt[0],popt[1],popt[2],popt[3],)-ydata)),weights=xdata[0]*xdata[1])
        print('MAE fit = {} eV'.format(MAE_int))
        self.MAE_fit = MAE_int
        
        #if self.MAE_fit > 2*self.conv_thr: 
        #    print('Fit not reliable, exit')
        #    return False
        #else:
        #    print('Fit reliable, continue...')
        
        if verbose: 
            print(max(xdata[0,:]),max(xdata[1,:])) #,popt[1]*popt[3])
            print('conv_thr, ',self.conv_thr)
        ###########Preliminary fit#################################
        
        self.X_fit = np.arange(min(xdata[0]),max(xdata[0])*10,self.delta_[0])
        self.Y_fit = np.arange(min(xdata[1]),max(xdata[1])*10,self.delta_[1])
                
        self.Zx_fit = fx(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2],popt[3])
        self.Zy_fit = fy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2])
        self.Zxy_fit = fxy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2])
        
        self.X_fit,self.Y_fit = np.meshgrid(self.X_fit,self.Y_fit)
        
        self.extra = popt[1]*popt[3]

        ###########Estimation of the plateaux corner###############
        
        if reference == 'extra':
            reference = self.extra
        else:
            self.Z_fit = f(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2],popt[3])  
            reference = self.Z_fit[-1,-1]
            
        if self.conv_thr_units=='%':
            thr = self.conv_thr*abs(reference)/100
        else:
            thr = self.conv_thr
            
        
        self.condition_conv_calc = np.where((abs(self.Zx_fit*self.delta_[0])<=thr/3) & \
                            (abs(self.Zy_fit*self.delta_[1])<=thr/3) & \
                            (abs(self.Zxy_fit*self.delta_[0] * self.delta_[1])<=thr/3))
        
        if len(self.X_fit[self.condition_conv_calc]) == 0 : return False
        if not b: b = max(max(xdata[0]),self.X_fit[self.condition_conv_calc][0]*1.5)
        if not g: g = max(max(xdata[1]),self.Y_fit[self.condition_conv_calc][0]*1.5)
            
        print('b: {}\ng: {}'.format(b,g))
        
        p = f(np.array((max(xdata[0,:]),max(xdata[1,:]))),popt[0],popt[1],popt[2],popt[3])
        p_H = f(np.array((b,g)),popt[0],popt[1],popt[2],popt[3])
        try:
            l = ydata[np.where((xdata[0] == max(xdata[0])) & (xdata[1] == max(xdata[1])))][0]
        except:
            l = ydata[-1]
        
        print('extra={} eV, \nlast calculation={} eV \nlast calculation from fit={} eV'.format(round(popt[3]*popt[1],3),
                                                                                          round(l,2),round(p,3)))
        
        if verbose: print('({},{}) highest point from fit = {} eV\n'.format(b,g,round(p_H,3)))
        if verbose: print('\nrelative err extra - last calculation = {}%'.format(round(100*abs((popt[3]*popt[1]-l)/(l)),3)))      
        if verbose: print('relative err extra - highest point from fit = {}%'.format(round(100*abs((popt[3]*popt[1]-p_H)/(p_H)),3)))
        
        self.X_fit = np.arange(min(xdata[0]),b+1,self.delta_[0])
        self.Y_fit = np.arange(min(xdata[1]),g+1,self.delta_[1])
        
        self.Z_fit = f(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2],popt[3])
        
        self.Zx_fit = fx(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2],popt[3])
        self.Zy_fit = fy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2])
        self.Zxy_fit = fxy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2])
        
        self.X_fit,self.Y_fit = np.meshgrid(self.X_fit,self.Y_fit)

       
        self.gradient_angle = popt[0]*popt[2]*np.sign(self.Z_fit[-1,-1])

        
        if plot:
            lw=10
            print('res min {}, res max {}'.format(min(self.res),max(self.res)))
            fig,ax = plt.subplots(figsize=[8,8])
            
            self.plot_scatter_contour_2D(fig,ax,
                                      self.X_fit,self.Y_fit,self.Z_fit,
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,
                                      just_points=True,bar=True)
            
            #self.plot_scatter_contour_2D(fig,ax,
            #                          getattr(self,self.var_[0]), getattr(self,self.var_[1]),self.res,
            #                          vmin=min(self.res),vmax=max(self.res),
            #                          marker='o',lw = 7,
            #                          colormap=colormap,label='all simulations',
            #                          just_points=True)
            
            self.plot_scatter_contour_2D(fig,ax,
                                      xdata[0],xdata[1],'black',
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,label='simulations',
                                      just_points=False)
                        
            if save : plt.savefig('plot_fit.png')

            
        return True
    

    def determine_next_calculation(self,
                                   overconverged_values=[],
                                   plot=False,
                                   colormap='gist_rainbow_r',
                                   reference = None,save=False):
        
        print('last point:{} eV'.format(self.Z_fit[-1,-1]))
        
        if reference == 'extra':
            reference = self.extra
        else:
            reference = self.Z_fit[-1,-1]
            
        if self.conv_thr_units=='%':
            thr = self.conv_thr*abs(reference)/100
        else:
            thr = self.conv_thr
        
        print(thr)
        condition = np.where((abs(reference-self.Z_fit)<=thr) & \
                            (abs(self.Zx_fit*self.delta_[0])<=thr) & \
                            (abs(self.Zy_fit*self.delta_[1])<=thr) & \
                            (abs(self.Zxy_fit*self.delta_[0]*self.delta_[1])<=thr))
        print(condition)
        print(self.Z_fit[condition])
        print('\n')
        
        print('Min G condition')
        print(self.Z_fit[condition][0])
        print(self.X_fit[condition][0])
        print(self.Y_fit[condition][0])
        
        self.condition = condition
        self.rectangle = ((self.X_fit[-1,-1]-self.X_fit[condition][0])/self.delta_[0])*((self.Y_fit[-1,-1]-self.Y_fit[condition][0])/self.delta_[1])
        self.rectangle = int(self.rectangle)
         
        conv_bands,conv_G = self.X_fit[condition][0],self.Y_fit[condition][0]
        conv_z = self.Z_fit[condition][0]
        
        self.next_step = {
            self.var_[0]:conv_bands,
            self.var_[1]:conv_G,
            self.what: conv_z,
            'already_computed':False,
        }
        
        if conv_bands in self.parameters[0,:] and conv_G in self.parameters[1,np.where(self.parameters[0,:]==conv_bands)]:
            self.next_step['already_computed'] = True
        
        if 'BndsRnXp' in self.var and 'GbndRnge' in self.var and len(self.var) > 2:
            self.next_step['GbndRnge'] = copy.deepcopy(self.next_step['BndsRnXp'])
        
        if plot:
            lw = 10
            fig,ax = plt.subplots(figsize=[8,8])
            
            self.plot_scatter_contour_2D(fig,ax,
                                      self.X_fit,self.Y_fit,'grey',
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,label='excluded points',
                                      just_points=True)
            
            self.plot_scatter_contour_2D(fig,ax,
                                      self.X_fit[condition], self.Y_fit[condition],self.Z_fit[condition],
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,
                                      label='converged points',
                                      just_points=True,bar = True)
            
            self.plot_scatter_contour_2D(fig,ax,
                                      self.parameters[0,:], self.parameters[1,:],'black',
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,
                                      just_points=True)  
            
            
            self.plot_scatter_contour_2D(fig,ax,
                                      conv_bands, conv_G,'red',
                                      vmin=min(self.res),vmax=max(self.res),
                                      marker='o',lw = lw,
                                      colormap=colormap,label='cheapest point',
                                      just_points=False)   
            
            if save : plt.savefig('plot_next.png')
        
        return self.next_step
    
    def check_the_point(self,old_hints={}):
        

        print(old_hints[self.what])
        print(self.result)
        print(self.result[(self.result[self.var_[0]]==old_hints[self.var_[0]]) & (self.result[self.var_[1]]==old_hints[self.var_[1]])][self.what].values)


        self.old_discrepancy =abs(old_hints[self.what] - self.result[(self.result[self.var_[0]]==old_hints[self.var_[0]]) & \
            (self.result[self.var_[1]]==old_hints[self.var_[1]])][self.what].values[0])
        
        self.index = [int(self.result[(self.result[self.var_[0]]==old_hints[self.var_[0]]) & \
            (self.result[self.var_[1]]==old_hints[self.var_[1]])].index.values[0])]

        print('Discrepancy with old prediction: {} eV'.format(self.old_discrepancy))
            
        if old_hints[self.var_[0]] == self.next_step[self.var_[0]] and old_hints[self.var_[1]] == self.next_step[self.var_[1]]:
            self.point_reached = True
        else:
            self.point_reached = False
            print('new point predicted.')
              
        return
    
    
    def analyse(self,old_hints={},reference = None, plot= False,save_fit=False,save_next = False,colormap='viridis'):
        
        self.check_passed = True
        error = 10

        power_laws = [1,2]
        for i in power_laws:
            for j in power_laws:
                print(i,j)
                self.fit_space_2D(fit=True,alpha=i,beta=j,plot=False,dim=10, colormap='viridis')
                if self.MAE_fit<error: 
                    ii,jj = i,j
                    error = self.MAE_fit

        print('\nBest power laws: {}, {}\n'.format(i,j))            
        
        self.check_passed = self.fit_space_2D(fit=True,alpha=1,beta=1,verbose=True,plot=plot,save=save_fit,colormap=colormap)
        if not self.check_passed: 
            self.point_reached = False
            self.new_grid = create_grid(
                edges=[min(self.parameters[0]),min(self.parameters[1]),max(self.parameters[0]),max(self.parameters[1])],
                delta=self.delta_,
                alpha=0.25,
                add = [[],[]],
                var=self.var_,
                shift=[2,2])
            return
            
        self.determine_next_calculation(plot=plot, colormap=colormap,save=save_next)
        self.point_reached = False
        
        if old_hints or self.next_step['already_computed']:
                if self.next_step['already_computed']: 
                    old_hints = self.next_step
                    self.point_reached = True
                self.check_the_point(old_hints)
                if reference == 'extra':
                    reference = self.extra
                else:
                    reference = self.Z_fit[-1,-1]
                    
                if self.conv_thr_units=='%':
                    factor = 100/abs(reference)
                else:
                    factor=1
                
                if self.old_discrepancy < self.conv_thr*factor: 
                    self.check_passed = True
                else:
                    self.check_passed = False

        #1 if check not passed but point reached, you need a new grid! 
        #2 if check passed and point reached, stop
        #3 if not old hints, you need to compute the next point.
        #4 if not old hints but/or already have the next point, check... follows 1 or 2
        
        if not self.check_passed and self.point_reached:
            self.next_step['new_grid'] = True
        else:
            self.next_step['new_grid'] = False

        return True