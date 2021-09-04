from __future__ import absolute_import
import numpy as np
from scipy import optimize
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
        
        self.p = []
        for k in self.p_val.keys():
            self.p.append(self.p_val[k])
            print(self.p_val[k])
        self.p = np.array(self.p)
        print(self.p)

        self.steps_ = self.steps

    def dummy_convergence(self,what): #solo window, thr e oversteps ---AAA generalize with all the "what", just a matrix . 
        self.delta_ = self.conv_array[what]-self.conv_array[what][-1]
            
        converged = self.delta_[-self.steps:][np.where(abs(self.delta_[-self.steps:])<=self.conv_thr)]
        if len(converged)<self.conv_window:
            is_converged = False
            oversteps = []
            converged_result = None
        else:
            is_converged = True
            oversteps = list(self.real[abs(self.real[what]-self.real[what].values[-1])<self.conv_thr].uuid)[1:]  
            l = len(oversteps)
            converged_result = self.conv_array[what][-l]
        
        hint={}
        for i in self.var:
            hint[i] = self.p[self.var.index(i),-len(oversteps)-1]
            
        return converged, is_converged, oversteps, converged_result, hint
            
    def newton_1D(self, what, evaluation='fit',): #'numerical'/'fit'
        perr = 10
        for i in [0.5,1,2,3]:
            f = lambda x,a,b: a/x**i + b
            try:
                popt,pcov = optimize.curve_fit(f,
                                           xdata=self.p[0,-self.steps:],  
                                           ydata=self.conv_array[what][-self.steps:],
                                           sigma=1/(self.p[0,-self.steps:]))

                perr_n = abs(np.average(f(self.p[0,-self.steps:],*popt)-self.conv_array[what][-self.steps:],))
                #print(perr_n,perr_n < perr)
                if perr_n < perr:
                    candidates = i
                    perr = perr_n
            except:
                pass
        
        f = lambda x,a,b: a/x**candidates + b
        fx = lambda x,a,b: -candidates*a/x**(candidates+1)
        fxx = lambda x,a,b: candidates*(candidates+1)*a/x**(candidates+2) 
        
        popt,pcov = optimize.curve_fit(f,
                                       xdata=self.p[0,-self.steps:],  
                                       ydata=self.conv_array[what][-self.steps:],
                                       )

        self.extra = popt[-1]
        self.gradient = fx(self.p[0,-1],*popt)
        self.laplacian = fxx(self.p[0,-1],*popt)
        
        is_converged = abs(self.extra-self.conv_array[what][-1] < self.conv_thr*4)
        
        guess = self.p[0,-1]+abs(self.gradient/self.laplacian)
        if not isinstance(self.stop,list): self.stop = [self.stop]
        new_metrics = int((self.stop[0]-guess)/(self.conv_thr/abs(popt[0]))**(1/candidates)-guess)

        hint = {self.var[0]:guess,'extra':self.extra,'new_metrics':new_metrics,
                self.var[0]+'_fit_converged':abs(popt[0]/self.conv_thr)**(1/candidates),
                'power_law':candidates}

        if guess > self.stop[0]:
            hint.pop('new_metrics')

        if evaluation=='numerical':
            self.num_gradient = np.zeros((len(self.variables),self.steps_fit))
            self.num_laplacian = np.zeros((len(self.variables),self.steps_fit))
            
            for i in range(len(self.variables)):
                self.num_gradient[i,:] = np.gradient(self.delta_[-self.steps:],self.p[i,-self.steps:])
                self.num_laplacian[i,:] = np.gradient(self.num_gradient[i,:],self.p[i,-self.steps:])
        
            return is_converged, self.p[0,-1]+abs(self.num_gradient/self.num_laplacian)
        else:
            return is_converged, hint 
        
    def newton_2D(self, what, extrapolation=False):

        if extrapolation: self.steps_ = self.steps*self.iter

        bb = self.p[0,-self.steps_:]
        g = self.p[1,-self.steps_:]
        homo = self.conv_array[what][-self.steps_:]
        perr= 10 
        for eb in [0.5,1,2,3]:
            for eg in [0.5,1,2,3]:

                exp_b = eb
                exp_g = eg
                def f(x,a,b,c,d): 
                    return (a/x[0]**exp_b +b)*(c/x[1]**exp_g+d)

                def f_x(x,a,b,c,d):
                    return (-exp_b*a/x[0]**(exp_b+1))*(c/x[1]**exp_g+d)

                def f_y(x,a,b,c,d): 
                    return (a/x[0]**exp_b +b)*(-exp_g*c/x[1]**(exp_g+1))

                def f_xx(x,a,b,c,d):
                    return (exp_b*(exp_b+1)*a/x[0]**(exp_b+2))*(c/x[1]**exp_g+d)

                def f_yy(x,a,b,c,d): 
                    return (a/x[0]**exp_b +b)*(exp_g*(exp_g+1)*c/x[1]**(exp_g+2))

                def f_xy(x,a,b,c,d): 
                    return (-exp_b*a/x[0]**(exp_b+1))*(-exp_g*c/x[1]**(exp_g+1))

                try:
                    popt,pcov = optimize.curve_fit(f,xdata=(bb,g),ydata=homo,sigma=1/(bb*g))

                    perr_n = abs(np.average(f((bb,g),*popt)-homo,))
                    #print(perr_n,perr_n < perr)
                    if perr_n < perr:
                        candidates = [eb,eg]
                        perr = perr_n
                except:
                    pass


        #create functions    
        exp_b, exp_g = candidates[:]
        def f(x,a,b,c,d): 
                return (a/x[0]**exp_b +b)*(c/x[1]**exp_g+d)

        def f_x(x,a,b,c,d):
                return (-exp_b*a/x[0]**(exp_b+1))*(c/x[1]**exp_g+d)

        def f_y(x,a,b,c,d): 
                return (a/x[0]**exp_b +b)*(-exp_g*c/x[1]**(exp_g+1))

        def f_xx(x,a,b,c,d):
                return (exp_b*(exp_b+1)*a/x[0]**(exp_b+2))*(c/x[1]**exp_g+d)

        def f_yy(x,a,b,c,d): 
                return (a/x[0]**exp_b +b)*(exp_g*(exp_g+1)*c/x[1]**(exp_g+2))

        def f_xy(x,a,b,c,d): 
                return (-exp_b*a/x[0]**(exp_b+1))*(-exp_g*c/x[1]**(exp_g+1))

        #fit    
        popt, pcov = optimize.curve_fit(f,xdata=(bb,g),ydata=homo,sigma=1/(bb*g))
        
        b = max(bb)
        gg = max(g)
        Gradient = np.zeros(2)
        Hessian = np.zeros((2,2))
        Gradient[0] = f_x((b,gg),*popt)
        Gradient[1] = f_y((b,gg),*popt)
        Hessian[0,0] = f_xx((b,gg),*popt)
        Hessian[0,1] = f_xy((b,gg),*popt)
        Hessian[1,0] = f_xy((b,gg),*popt)
        Hessian[1,1] = f_yy((b,gg),*popt)

        concavity = Hessian[0,0]*Hessian[1,1]
        next_point = np.array([max(bb),max(g)])-np.dot(np.linalg.inv(Hessian),Gradient)
        
        self.extra = popt[-1]*popt[-3]

        new_metrics = [int((self.stop[0]-next_point[0])/(abs(popt[0]/self.conv_thr)**(1/candidates[0])-next_point[0])),
                       int((self.stop[1]-next_point[1])/(abs(popt[1]/self.conv_thr)**(1/candidates[1])-next_point[1]))]
        infos = {'concavity':concavity,'extra':self.extra,'new_metrics':new_metrics,'power_law':candidates}
        for h in range(len(next_point)):
            infos[self.var[h]] = next_point[h]
            infos[self.var[h]+'_fit_converged']=(abs(popt[0*2]/self.conv_thr))**(1/candidates[h])

        for h in range(len(next_point)):
            if next_point[h]>self.stop[h]:
                infos.pop('new_metrics')
                break


        return abs(homo[-1]-popt[1]*popt[3])<self.conv_thr*4 and concavity>0,infos
    
    def analysis(self,):
        
        converged, is_converged, oversteps, converged_result,hint = self.dummy_convergence(what=self.quantities[-1])
        
        if 'dummy' in self.convergence_algorithm:            
            hint = None
            is_converged_fit = True #no fit
        
        elif 'newton_1D' in self.convergence_algorithm:
            is_converged_fit, hint = self.newton_1D(what=self.quantities[-1])
        
        elif 'newton_2D_extra' in self.convergence_algorithm:
            finish = self.max_iterations == self.iter
            if finish: is_converged_fit, hint = self.newton_2D(what=self.quantities[-1],extrapolation=True)
            
            is_converged, is_converged_fit, oversteps =  finish, finish, []
        
        elif 'newton_2D' in self.convergence_algorithm:
            is_converged_fit, hint = self.newton_2D(what=self.quantities[-1])
           
        return is_converged and is_converged_fit, oversteps, hint