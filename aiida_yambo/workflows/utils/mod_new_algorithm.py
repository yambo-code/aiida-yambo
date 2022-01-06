from __future__ import absolute_import

import numpy as np
from scipy import optimize
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
from aiida_yambo.utils.common_helpers import *

def create_grid(edges=[],delta=[],alpha=0.25,add = [[],[]]):
    
    b_min = edges[0]
    b_max = edges[2]
    g_min = edges[1]
    g_max = edges[3]
    
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
    
    return b,G #A,B,C,D,E,F


def build_data(b,G,node_id,what,):
    
    result = pd.DataFrame(load_node(node_id).outputs.history.get_dict())
    
    pw = find_pw_parent(load_node(load_node(result.uuid.values[-1]).called[0].called[0].pk))
    bande = pw.outputs.output_band.get_bands()
    
    r = []
    indexing_for_timing = []
    #b,G = #list(result.BndsRnXp.values),list(result.NGsBlkXp.values)
    
    for i,j in list(zip(b,G)):
        r.append(result[(result.BndsRnXp==i) & (result.NGsBlkXp==j)][what].values[0])
        indexing_for_timing.append(int(result[(result.BndsRnXp==i) & (result.NGsBlkXp==j)].index[0]))
    
    
    data = (np.array([b[:],G]),np.array(r))
    
    return data, bande, result

############################################################################
############################################################################

class The_Predictor():
    
    '''Class to analyse the convergence behaviour of a system
    using the new algorithm of MB:
    1 - Interpolate the space available using the 
        scipy.interpolate.CloughTocher2DInterpolator 
        interpolation method [P. Alfeld, Computer Aided Geometric Design, 1, 169 (1984)] 
    2 - Understand if the simulations are ok: they are ok if all the space in the middle 
        satisfy Zx*Zy > 0. Not sure about this. F_2 is not ok with that
    3 - If all the simulations are ok, fit them. Otherwise fit only the last region of
        interpolated points satisfying the condition. If there are no such a point, you 
        need to produce a new set of simulations with higher parameters.'''
    
    def __init__(self, infos):
        for k,v in infos.items():
            setattr(self,k,copy.deepcopy(v))
        
        if not hasattr(self,'Fermi'): self.Fermi=0
        self.bb, self.GG = copy.deepcopy(list(self.result.BndsRnXp.values)),copy.deepcopy(list(self.result.NGsBlkXp.values))
        self.res = copy.deepcopy(self.result[self.what].values[:] + self.Fermi)
        self.bb_Ry = copy.deepcopy(self.bande[0,np.array(self.bb)-1]/13.6)
        self.r[:] = self.r[:] + self.Fermi
        self.G = copy.deepcopy(self.G)
        
        print('G',self.G)
        
    
    def plot_scatter_contour(self,x,y,z,colormap='gist_rainbow_r',label=''):       
        
        fig,ax = plt.subplots(figsize=[7,7])

        scatter = ax.scatter(x, y, 100, 
                       c=z,marker='o',
                       label=label,
                       vmin=min(z),vmax=max(z),
                       cmap=colormap)

        ax.legend(fontsize=13)
        cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
        ax.set_xlabel('# of bands',fontdict={'fontsize':20})
        ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
        ax.tick_params(axis='both',labelsize=20)

        cmap.set_label('eV', rotation=0,labelpad=36,fontsize=20)
        cmap.ax.tick_params(labelsize=20)

        ax.grid()

        l_ = list(set(self.bb))
        l_.sort()
        #l__ = list(set(result.BndsRnXp.values))
        l__ = list(set(np.round(self.bb_Ry,0)))
        l__.sort()
        ax2 = ax.twiny()
        ax2.set_xticks(l_[::3])
        ax2.set_xbound(ax.get_xbound())
        ax2.set_xticklabels(l__[::3],fontdict={'size':20})
        ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})
            
    def interpolate(self,plot=False,dim=100,colormap='gist_rainbow_r',interp_model='CT'):
        
        from scipy.interpolate import CloughTocher2DInterpolator,interp2d,NearestNDInterpolator
        from scipy.interpolate import LinearNDInterpolator,griddata
        from scipy.interpolate import bisplrep,bisplev
        
        x = self.G[0,:]
        y = self.G[1,:]
        z = self.r[:]
        X = np.arange(min(x), max(x)+1,self.delta[0]) #np.linspace(min(x), max(x),dim)
        Y = np.arange(min(y), max(y)+1,self.delta[1]) #np.linspace(min(y), max(y),dim)
        self.X, self.Y = np.meshgrid(X, Y)  # 2D grid for interpolation
        #interp = NearestNDInterpolator(list(zip(x, y)), z)
        if interp_model == 'CT':
            interp = CloughTocher2DInterpolator(list(zip(x, y)), z)
            self.Z = interp(self.X, self.Y)
        elif interp_model == 'NearestND':
            interp = NearestNDInterpolator(list(zip(x, y)), z)
            self.Z = interp(self.X, self.Y)
        elif interp_model == 'LinearND':
            interp = LinearNDInterpolator(list(zip(x, y)), z)
            self.Z = interp(self.X, self.Y)
        elif interp_model == 'griddata':
            self.Z = griddata(list(zip(x, y)), z, (self.X,self.Y),method='cubic')
        elif interp_model == 'Bspline':
            tck = bisplrep(x, y, z, s=0)
            self.Z = bisplev(self.X, self.Y, tck)
        
        self.average_error_interp = np.average(abs(z-interp(x,y)))
        
        self.interp_model = interp_model
        
        if plot:
            
            fig,ax = plt.subplots(figsize=[7,7])
            scatter= ax.scatter(self.X, self.Y, 100, c=self.Z,
                                vmin=min(self.res),vmax=max(self.res),
                                cmap=colormap,marker='s',
                                label='points from interpolation')

            ax.scatter(x, y, 100, 
                       c='black',marker='s',
                       label='interpolated simulations',
                       vmin=min(self.res),vmax=max(self.res),cmap=colormap,
                       linewidth=7)

            ax.scatter(self.bb, self.GG, 100, 
                       c=self.res,marker='o',
                       label='all simulations',
                       vmin=min(self.res),vmax=max(self.res),
                       cmap=colormap)

            ax.legend(fontsize=13)
            cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
            ax.set_xlabel('# of bands',fontdict={'fontsize':20})
            ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            cmap.set_label('eV', rotation=0,labelpad=36,fontsize=20)
            cmap.ax.tick_params(labelsize=20)

            ax.grid()


            l_ = list(set(self.bb))
            l_.sort()
            #l__ = list(set(result.BndsRnXp.values))
            l__ = list(set(np.round(self.bb_Ry,0)))
            l__.sort()
            ax2 = ax.twiny()
            ax2.set_xticks(l_[::3])
            ax2.set_xbound(ax.get_xbound())
            ax2.set_xticklabels(l__[::3],fontdict={'size':20})
            ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})

##################################################################
    def subset(self,inf=0):
        '''conditions for convergence surface. I don't think that
        the actual conditions are corrects, as Zx and Zy can have opposite sign. Anyway, a sign change curvatures or
        slopes is not good. Should be a sort of backpropagation, stopping when we have these problems.
        '''
        
        self.Zx = np.zeros(np.shape(self.Z))
        self.Zy = np.zeros(np.shape(self.Z))
        
        self.Zxx = np.zeros(np.shape(self.Z))
        self.Zyy = np.zeros(np.shape(self.Z))
        
        self.Zxy = np.zeros(np.shape(self.Z))
        self.Zyx = np.zeros(np.shape(self.Z))
        
        for i in range(np.shape(self.Z)[0]):
            #print(X[i])
            self.Zx[i,:] = np.gradient(self.Z[i,:],self.X[i,:])
            self.Zxx[i,:] = np.gradient(self.Zx[i,:],self.X[i,:])
            self.Zxy[i,:] = np.gradient(self.Zy[i,:],self.X[i,:])

        for j in range(np.shape(self.Z)[1]):
            #print(X[i])
            self.Zy[:,j] = np.gradient(self.Z[:,j],self.Y[:,j])
            self.Zyy[:,j] = np.gradient(self.Zy[:,j],self.Y[:,j])
            self.Zyx[:,j] = np.gradient(self.Zx[:,j],self.Y[:,j])
         
        condition_below = (self.Zx*self.Zy>=0) # & (self.Zx*self.Zxx>0) & (self.Zy*self.Zyy>0)
        
        try:
            inf_X, inf_Y = np.max(self.X[condition_below]), \
                           np.max(self.Y[condition_below])
            print('condition below successfull')
        except Exception as err:
            print(err)
            inf_X, inf_Y = -1,-1
            print('no suitable points, so we need to increase the space')
            
        condition_upper = np.where((self.X >= inf_X) & (self.Y >= inf_Y) & (np.isnan(self.Z) == False))
        condition_upper_points = np.where((self.G[0,:] >= inf_X) & (self.G[1,:] >= inf_Y))
        #print(condition_upper)
        self.subset_ = {
            'Z':self.Z[condition_below],
            'Y':self.Y[condition_below],
            'X':self.X[condition_below],
            'enough_int':len(self.Z[condition_below])>=4,
            'z':self.r[condition_upper_points],
            'y':self.G[1,condition_upper_points][0],
            'x':self.G[0,condition_upper_points][0],
            'enough_ext': len(self.r[condition_upper_points])>=4,
        }
        
        return self.subset_
################################################################

    def fit_space(self,fit=False,alpha=1,beta=1,verbose=False,interpolation=False,plot=False,dim=100,colormap='gist_rainbow_r',b=None,g=None):
        
        if self.conv_thr_units=='%':
            factor = 100
        else:
            factor=1
        
        f = lambda x,a,b,c,d: (a/x[0]**alpha + b)*( c/x[1]**beta + d)
        fx = lambda x,a,c,d: -alpha*a/(x[0]**(alpha+1))*( c/x[1] + d)
        fy = lambda x,a,b,c: (a/x[0] + b)*( -beta*c/x[1]**(beta+1) )
        
        fxy = lambda x,a,c: -alpha*a/(x[0]**(alpha+1))*( -beta*c/x[1]**(beta+1))
        
        if fit:  #fit: 
            xdata,ydata = np.array((self.G[0,:],self.G[1,:])),self.r[:]
            print('fitting all simulations.')
        elif interpolation: 
            xdata = np.array((self.X.reshape((len(self.X[0,:])*len(self.X[:,0]))),self.Y.reshape((len(self.X[0,:])*len(self.X[:,0]))))) 
            ydata = self.Z.reshape((len(self.X[0,:])*len(self.X[:,0])))
            print('fitting all interpolated points.')
        elif self.subset_['enough_ext']:  #fit: 
            xdata,ydata = np.array((self.subset_['x'],self.subset_['y'])),self.subset_['z']
            print('fitting the suitable simulations.')
        elif self.subset_['enough_int']: 
            xdata,ydata = np.array((self.subset_['X'],self.subset_['Y'])),self.subset_['Z']
            print('fitting suitable interpolated points.')
        else:
            print('no suitable points, we need to create a new grid.')
            return False
        
        #print(xdata[0]*xdata[1])
            
        popt,pcov = curve_fit(f,xdata=xdata,
                      ydata=ydata,sigma=1/(xdata[0]*xdata[1]),
                      bounds=([-np.inf,-np.inf,-np.inf,-np.inf],[np.inf,np.inf,np.inf,np.inf]))
        
        MAE_int = abs((np.average(f(xdata,popt[0],popt[1],popt[2],popt[3],)-ydata)))
        print('MAE fit = {} eV'.format(MAE_int))
        self.MAE_fit = MAE_int
        
        if verbose: print(max(xdata[0,:]),max(xdata[1,:])) #,popt[1]*popt[3])
        ###########Preliminary fit#################################
        
        self.X_fit = np.arange(min(xdata[0]),max(xdata[0])*10,self.delta[0])
        self.Y_fit = np.arange(min(xdata[1]),max(xdata[1])*10,self.delta[1])
                
        self.Zx_fit = fx(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2],popt[3])
        self.Zy_fit = fy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2])
        self.Zxy_fit = fxy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2])
        
        self.X_fit,self.Y_fit = np.meshgrid(self.X_fit,self.Y_fit)
        
        ###########Estimation of the plateaux corner###############
        self.condition_conv_calc = np.where((abs(factor*self.Zx_fit*self.delta[0])<=self.conv_thr/10) & \
                            (abs(factor*self.Zy_fit*self.delta[1])<=self.conv_thr/10) & \
                            (abs(factor*self.Zxy_fit*self.delta[0] * self.delta[1])<=self.conv_thr/10))
        
        if not b: b = self.X_fit[self.condition_conv_calc][0]
        if not g: g = self.Y_fit[self.condition_conv_calc][0]
            
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
        
        self.X_fit = np.arange(min(xdata[0]),b+1,self.delta[0])
        self.Y_fit = np.arange(min(xdata[1]),g+1,self.delta[1])
        
        self.Z_fit = f(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2],popt[3])
        
        self.Zx_fit = fx(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2],popt[3])
        self.Zy_fit = fy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[1],popt[2])
        self.Zxy_fit = fxy(np.meshgrid(self.X_fit,self.Y_fit),popt[0],popt[2])
        
        self.X_fit,self.Y_fit = np.meshgrid(self.X_fit,self.Y_fit)

        self.extra = popt[1]*popt[3]
        self.gradient_angle = popt[0]*popt[2]*np.sign(self.Z_fit[-1,-1])


        
        if plot:
            
            fig,ax = plt.subplots(figsize=[7,7])
            scatter= ax.scatter(self.X_fit, self.Y_fit, 100, c=self.Z_fit,
                                vmin=min(self.res),vmax=max(self.res),
                                cmap=colormap,marker='s',
                                label='points from fit')

            ax.scatter(xdata[0],xdata[1], 100, 
                       c='black',marker='s',
                       label='used points',
                       vmin=min(self.res),vmax=max(self.res),cmap=colormap,
                       linewidth=7)

            ax.scatter(self.bb, self.GG, 100, 
                       c=self.res,marker='o',
                       label='all simulations',
                       vmin=min(self.res),vmax=max(self.res),
                       cmap=colormap)

            ax.legend(fontsize=13)
            cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
            ax.set_xlabel('# of bands',fontdict={'fontsize':20})
            ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            cmap.set_label('eV', rotation=0,labelpad=36,fontsize=20)
            cmap.ax.tick_params(labelsize=20)

            ax.grid()

            l_ = list(set(self.bb))
            l_.sort()
            #l__ = list(set(result.BndsRnXp.values))
            l__ = list(set(np.round(self.bb_Ry,0)))
            l__.sort()
            ax2 = ax.twiny()
            ax2.set_xticks(l_[::3])
            ax2.set_xbound(ax.get_xbound())
            ax2.set_xticklabels(l__[::3],fontdict={'size':20})
            ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})
        
            #plt.savefig('hBN_multivariate.pdf')
        return True
    
    def time_estimation(self,plot=False,dim=20,colormap='gist_rainbow_r',units='minutes'):
        
        units_of_time={'seconds':1,'minutes':60,'hours':3600}
        
        t=[]
        for i in self.result.uuid:
            t.append(load_node(i).outputs.output_parameters.get_dict()['last_time']/units_of_time[units])
            #print(t[-1])
        
        time = lambda x,a,b,c,d,e: (a*x[0]+e)*(b*x[1]**3+c*x[1]**2+d*x[1])
        time_coeff,time_cov = curve_fit(time,np.array([self.result.BndsRnXp.values, \
                                                       list(self.result.NGsBlkXp.values)]), \
                                        t)
        
    
        self.time_fit = time(np.array([self.X_fit,self.Y_fit]),
                          time_coeff[0],
                          time_coeff[1],
                          time_coeff[2],
                          time_coeff[3],
                          time_coeff[4])
        
        if plot:
            
            fig,ax = plt.subplots(figsize=[7,7])

            ax.scatter(self.bande[0,self.result.BndsRnXp.values-1]/13.6,self.result.NGsBlkXp.values, 100, 
                       c=t,marker='s',
                       label='used points',
                       vmin=min(t),vmax=max(t),
                       cmap=colormap,
                       )
            
            scatter= ax.scatter(self.X_fit, self.Y_fit, 100, c=self.time_fit,
                                vmin=min(t),vmax=max(t),
                                cmap=colormap,marker='o',
                                label='points from fit')

            ax.legend(fontsize=13)
            cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
            ax.set_xlabel('# of bands',fontdict={'fontsize':20})
            ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            cmap.set_label(units, rotation=15,labelpad=36,fontsize=20)
            cmap.ax.tick_params(labelsize=20)

            ax.grid()

            l_ = list(set(self.bb))
            l_.sort()
            #l__ = list(set(result.BndsRnXp.values))
            l__ = list(set(np.round(self.bb_Ry,0)))
            l__.sort()
            ax2 = ax.twiny()
            ax2.set_xticks(l_[::3])
            ax2.set_xbound(ax.get_xbound())
            ax2.set_xticklabels(l__[::3],fontdict={'size':20})
            ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})
            
    def determine_next_calculation(self,
                                   overconverged_values=[],
                                   plot=False,
                                   colormap='gist_rainbow_r',
                                   reference = None):
        
        print('last point:{} eV'.format(self.Z_fit[-1,-1]))
        
        if reference == 'extra':
            reference = self.extra
        else:
            reference = self.Z_fit[-1,-1]
            
        if self.conv_thr_units=='%':
            factor = 100/abs(reference)
        else:
            factor=1
        
        #print(self.Zy_fit)
        condition = np.where((abs(factor*(reference-self.Z_fit))<=self.conv_thr) & \
                            (abs(factor*self.Zx_fit*self.delta[0])<=self.conv_thr) & \
                            (abs(factor*self.Zy_fit*self.delta[1])<=self.conv_thr) & \
                            (abs(factor*self.Zxy_fit*self.delta[0]*self.delta[1])<=self.conv_thr))
        print(condition)
        print(self.Z_fit[condition])
        print('\n')
        
        print('Time condition')
        print(self.Z_fit[condition][self.time_fit[condition].argmin()])
        print(self.X_fit[condition][self.time_fit[condition].argmin()])
        print(self.Y_fit[condition][self.time_fit[condition].argmin()])
        
        #print(np.where((self.X_fit**2+self.Y_fit**2) == np.max(self.X_fit**2+self.Y_fit**2)))
        
        print('Min G condition')
        print(self.Z_fit[condition][0])
        print(self.X_fit[condition][0])
        print(self.Y_fit[condition][0])
        
        self.condition = condition
        self.rectangle = ((self.X_fit[-1,-1]-self.X_fit[condition][0])/self.delta[0])*((self.Y_fit[-1,-1]-self.Y_fit[condition][0])/self.delta[1])
        self.rectangle = int(self.rectangle)
        
        conv_bands,conv_G = self.X_fit[condition][self.time_fit[condition].argmin()],self.Y_fit[condition][self.time_fit[condition].argmin()]
        conv_z = self.Z_fit[condition][self.time_fit[condition].argmin()]
        
        if self.X_fit[condition][self.time_fit[condition].argmin()]==self.X_fit[condition][0]:
            if self.Y_fit[condition][self.time_fit[condition].argmin()]>=self.Y_fit[condition][0]:
                conv_bands,conv_G = self.X_fit[condition][0],self.Y_fit[condition][0]
                conv_z = self.Z_fit[condition][0]
            
        next_step = {
            'BndsRnXp':conv_bands,
            'NGsBlkXp':conv_G,
            self.what: conv_z,
        }
        
        if plot:
            
            fig,ax = plt.subplots(figsize=[7,7])
            scatter= ax.scatter(self.X_fit[condition], self.Y_fit[condition], 100, 
                                c=self.Z_fit[condition],
                                vmin=min(self.res),
                                vmax=max(self.res),
                                cmap=colormap,marker='s',
                                label='converged points')
            
            ax.scatter(conv_bands, 
                       conv_G, 
                       100, 
                       #c=self.Z_fit[condition][self.time_fit[condition].argmin()],
                       vmin=min(self.res),
                       vmax=max(self.res),
                       c='red',marker='s',
                       label='cheapest point')

            ax.legend(fontsize=13,loc='upper right')
            cmap = fig.colorbar(scatter, shrink=0.5, aspect=7, pad=0.01)
            ax.set_xlabel('# of bands',fontdict={'fontsize':20})
            ax.set_ylabel('PW (Ry)',fontdict={'fontsize':20})
            ax.tick_params(axis='both',labelsize=20)

            cmap.set_label('eV', rotation=0,labelpad=36,fontsize=20)
            cmap.ax.tick_params(labelsize=20)

            ax.grid()

            l_ = list(set(self.bb))
            l_.sort()
            #l__ = list(set(result.BndsRnXp.values))
            l__ = list(set(np.round(self.bb_Ry,0)))
            l__.sort()
            ax2 = ax.twiny()
            ax2.set_xticks(l_[::3])
            ax2.set_xbound(ax.get_xbound())
            ax2.set_xticklabels(l__[::3],fontdict={'size':20})
            ax2.set_xlabel('KS states (Ry)',fontdict={'size':20})
            
            #plt.savefig('hBN_pred.pdf')
        
        return next_step