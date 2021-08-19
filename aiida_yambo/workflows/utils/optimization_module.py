from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit, minimize
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms

class Convergence_evaluator(): 
    
    def __init__(self, **kwargs): #lista_YamboIn, conv_array, parametri_da_conv(se lista fai fit multidimens), thr, window
        
        for k,v in kwargs['calc_dict'].items():
            setattr(self, k, v)
        for k,v in kwargs.items():
            if k != 'calc_dict': setattr(self, k, v)
        print(kwargs['calc_dict'])
        

        self.hint = {}
        self.concavity = 1
        self.extrapolated = 1
        if not hasattr(self,'power_law'): self.power_law = 1 
        
        self.p = []      
        if 'univariate' in self.convergence_algorithm:
            self.variables = self.var
            
            for param in self.var:
                self.p.append(self.p_val[param][:])
            self.steps_fit = self.steps*self.iter
            
        elif 'multivariate' in self.convergence_algorithm:
            self.variables = self.parameters
            self.steps_fit = self.steps*self.iter #or something........
            for param in self.parameters:
                self.p.append(self.p_val[param][:])
        
        print(self.variables)
        self.p = np.array(self.p)

    def dummy_convergence(self,what): #solo window, thr e oversteps ---AAA generalize with all the "what", just a matrix . 
        self.delta_ = self.conv_array[what]-self.conv_array[what][-1]
            
        converged = self.delta_[-self.conv_window:][np.where(abs(self.delta_[-self.conv_window:])<=self.conv_thr)]
        if len(converged)<self.conv_window:
            is_converged = False
            oversteps = 0
            converged_result = None
        else:
            is_converged = True
            oversteps = len(converged)
            for overstep in range(self.conv_window+1,len(self.delta_)+1):
                overconverged = self.delta_[-overstep:][np.where(abs(self.delta_[-overstep:])<=self.conv_thr)]
                if oversteps < len(overconverged):
                    oversteps = len(overconverged)
                else:
                    break     
            converged_result = self.conv_array[what][-oversteps]
            
        return converged, is_converged, oversteps-1, converged_result
    
    def convergence_function(self,xv,*args): #con fit e previsione parametri a convergenza con la thr
        if isinstance(self.power_law,int): self.power_law = [self.power_law]*len(self.parameters)
        y = 1.0
        for i in range(len(xv)):
            A=args[2*i]
            B=args[2*i+1]
            xval=xv[i]
            y = y * ( A/xval + B)
        return y
    
    def fit_prediction(self,what): 
        
        #we can do a fit for 1D or ND spaces... 
        #weights 
        sig = self.p[0,-self.steps_fit:]
        for i in range(1,len(self.variables)):
            sig = sig*self.p[i,-self.steps_fit:]/max(self.p[i,-self.steps_fit:])
        
        extra, pcov = curve_fit(self.convergence_function,
                                self.p[:len(self.variables),-self.steps_fit:],
                                self.conv_array[what][-self.steps_fit:],
                                p0=[1,1]*len(self.variables),
                                sigma=1/sig)
        self.extra = extra
        self.perr = np.average(abs(self.convergence_function(self.p[:len(self.variables),-self.steps_fit:],
                                                            *self.extra)-self.conv_array[what][-self.steps_fit:]),weights=sig)
        
        self.gradient = np.zeros((len(self.variables),self.steps_fit))
        self.laplacian = np.zeros((len(self.variables),self.steps_fit))
        for i in range(len(self.variables)):
            a = self.extra[2*i]
            b = self.extra[2*i+1]
            print(a,b,self.variables[i])
            if len(self.variables) > 1: self.concavity = a*self.concavity
            self.extrapolated = b*self.extrapolated  
            
            delta_ = self.p[i,-1] - self.p[i,-2]
            
            self.gradient[i,:] = -a/self.p[i,:]**2
            self.laplacian[i,:] = 2*a/self.p[i,:]**3
            for j in range(len(self.variables)):
                if i == j:
                    continue
                else:
                    self.gradient[i,:] *= self.extra[2*j]/self.p[j,:] + self.extra[2*j+1]
                    self.laplacian[i,:] *= self.extra[2*j]/self.p[j,:] + self.extra[2*j+1]
            
    def newton_method(self, evaluation='numerical',): #'numerical'/'analytical'
        
        if evaluation=='numerical':
            self.num_gradient = np.zeros((len(self.variables),self.steps_fit))
            self.num_laplacian = np.zeros((len(self.variables),self.steps_fit))
            
            for i in range(len(self.variables)):
                self.num_gradient[i,:] = np.gradient(self.delta_[-self.steps:],self.p[i,-self.steps:])
                self.num_laplacian[i,:] = np.gradient(self.num_gradient[i,:],self.p[i,-self.steps:])
        
            return self.num_gradient/self.num_laplacian
        else:
            return self.gradient/self.laplacian
        
    def conjugate_gradient(self,k=2,s_0=0):
        num_grad = np.zeros((len(c.parameters),c.steps))
        hessian_matrix = np.zeros((len(c.parameters),len(c.parameters),c.steps))
        for i in range(len(c.parameters)):
                #num_grad = self.delta[-self.steps_fit:]*(1/self.delta_x[i,-self.steps_fit:])
                num_grad[i] = np.gradient(c.delta_[-c.steps:],c.p[i,-c.steps:])
                for j in range(len(c.parameters)):
                    hessian_matrix[i,j] = np.gradient(num_grad[i],c.p[j,-c.steps:])
        
        if not isinstance(s_0,int): 
            s_k = - num_grad[:,-k] + s_0*(np.dot(num_grad[:,-k].transpose(),num_grad[:,-k])/np.dot(s_0.transpose(),s_0))
        else:
            s_k = -num_grad[:,-k]
            
        alfa = -np.dot(num_grad[:,-k].transpose(),s_k)/np.dot(s_k.transpose(),np.dot(hessian_matrix[:,:,-k],s_k))
        return alfa*num_grad[:,-k], s_k
    
    def analysis(self,):
        hint = {}
        
        converged, is_converged, oversteps, converged_result = self.dummy_convergence(what=self.quantities[-1])
        if 'dummy' in self.convergence_algorithm:
            print(self.convergence_algorithm)
            return is_converged, oversteps, None
        
        if 'univariate' in self.convergence_algorithm:
            print(self.convergence_algorithm)
            for v in self.variables:
                self.fit_prediction(what=self.quantities[-1])
                hint[v] = self.p[self.variables.index(v),-1] - self.newton_method(evaluation = self.convergence_algorithm.split('_')[-1])[self.variables.index(v),-1]
                if self.p[self.variables.index(v),-1] > 100 or v in ['BndsRnXp','GbndRnge']:
                    hint[v] = int(hint[v])
                #    hint[v] = int(round(hint[v],-1))
                elif self.p[self.variables.index(v),-1] < 100 and not 'mesh' in v:
                    hint[v] = int(hint[v])
                #    hint[v] = int(hint[v])+int(hint[v])%2
                
            if self.extrapolated: hint['extra'] = round(self.extrapolated,3)
            if self.concavity < 0: is_converged = False #wrong concavity in search univariate multiparams (1D diagonal line)

            return is_converged, oversteps, hint