from __future__ import absolute_import
import numpy as np
from scipy import optimize
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
from aiida_yambo.utils.common_helpers import *

class Convergence_evaluator(): 
    
    def __init__(self, **kwargs): #lista_YamboIn, conv_array, parametri_da_conv(se lista fai fit multidimens), thr, window
        
        for k,v in kwargs['calc_dict'].items():
            setattr(self, k, v)
        for k,v in kwargs.items():
            if k != 'calc_dict': setattr(self, k, v)
        print(kwargs['calc_dict'])
        
        self.p = []
        for k in self.p_val.keys():
            if k == 'mesh':continue
            self.p.append(self.p_val[k])
            print(self.p_val[k])
        self.p = np.array(self.p)
        print(self.p)

        self.steps_ = self.steps

    def ratio_evaluator(self,what):
        Ry = np.array(list(set(self.workflow_dict.NGsBlkXp)))
        Ry.sort()
        self.PW_G = Ry
        p=[]
        calcs = []

        if len(Ry)<3:
            return False

        for i in Ry: 
            p.append(self.workflow_dict[(self.workflow_dict.NGsBlkXp==i) & (self.workflow_dict.useful==True)]['BndsRnXp'].values[-1])
            calcs.append(self.workflow_dict[(self.workflow_dict.NGsBlkXp==i) & (self.workflow_dict.useful==True)]['uuid'].values[-1])
        b_index = np.array(p)
        pw = find_pw_parent(load_node(self.workflow_dict['uuid'].values[-1]))
        b = pw.outputs.output_band.get_bands()
        valence = int(pw.outputs.output_parameters.get_dict()['number_of_electrons']/2)

        lin=0

        lim_u=len(Ry)+1
        lim_d=0

        #if lin:
        if 1:
            aa_lin,bb_lin = np.polyfit(Ry[lim_d:lim_u],b[0,b_index[lim_d:lim_u]-1]/13.6,deg=1)
            f_lin = lambda x,a,b: a*x+b
            error_lin = np.sqrt(np.average((f_lin(Ry[lim_d:lim_u],aa_lin,bb_lin)-b[0,b_index[lim_d:lim_u]-1]/13.6)**2))
        #else:    
            f = lambda x,a,b: a/x + b
            aa,bb = curve_fit(f,Ry[lim_d:lim_u],b[0,b_index[lim_d:lim_u]-1]/13.6,sigma=1/np.array(Ry[lim_d:lim_u]))

            bb = aa[1]
            aa = aa[0]
            error = np.sqrt(np.average((f(Ry[lim_d:lim_u],aa,bb)-b[0,b_index[lim_d:lim_u]-1]/13.6)**2))
        
        maps_bands=[]
        maps_Ry_lin=[]
        maps_Ry=[]
        for i in range(1,1+len(b[0,:])):
            maps_Ry_lin.append((b[0,i-1]/13.6-bb_lin)/(aa_lin))
            maps_Ry.append(((b[0,i-1]/13.6-bb)/(aa))**(-1))
            maps_bands.append(i)
        
        self.b_index = b_index
        self.PW_G = Ry
        self.calcs_diagonal = calcs
        self.b_energy_Ry = b[0,b_index[lim_d:lim_u]-1]/13.6
        self.quantity = []
        for i in Ry[:-1]:
                self.quantity.append(self.workflow_dict[(self.workflow_dict.NGsBlkXp==i) & (self.workflow_dict.useful==True)][what].values[-1])

        self.quantity.append(self.workflow_dict[(self.workflow_dict.NGsBlkXp==Ry[-1])][what].values[-self.steps]) #self.oversteps])

        self.quantity = np.array(self.quantity)

        return True

    def dummy_convergence(self,what,ratio=False,diagonal=False): #solo window, thr e oversteps ---AAA generalize with all the "what", just a matrix . 
        
        if ratio:
            self.delta_ = abs((self.b_energy_Ry-self.b_energy_Ry[-1]))
            if self.conv_thr_units == 'eV': self.delta_ = abs((self.b_energy_Ry-self.b_energy_Ry[-1])/self.b_energy_Ry[-1])
            conv_thr = 1e-1
        elif diagonal:
            self.delta_ = abs((self.quantity-self.quantity[-1])/self.quantity[-1]) #abs((self.quantity-self.quantity[-1])/self.quantity[-1])
            if self.conv_thr_units == 'eV': self.delta_ = abs((self.quantity-self.quantity[-1]))
            conv_thr=self.conv_thr
        else:
            self.delta_ = abs((self.conv_array[what]-self.conv_array[what][-1])/self.conv_array[what][-1]) #abs((self.conv_array[what]-self.conv_array[what][-1])/self.conv_array[what][-1])
            if self.conv_thr_units == 'eV': self.delta_ = abs((self.conv_array[what]-self.conv_array[what][-1]))
            conv_thr=self.conv_thr
        #converged = self.delta_[-self.steps:][np.where(abs(self.delta_[-self.steps:])<=self.conv_thr)]
        converged = []
        for i in range(1,len(self.delta_)+1):
            if abs(self.delta_[-i])>conv_thr:
                break
            else:
                converged.append(list(self.real.uuid)[-i])
        self.converged = converged

        if len(converged)<self.conv_window:
            is_converged = False
            oversteps = []
            converged_result = None
        else:
            is_converged = True
            if ratio or diagonal:
                oversteps =  list(self.workflow_dict[(self.workflow_dict.NGsBlkXp>self.PW_G[-len(converged)])].uuid.values[:])
                oversteps_Ry =  set(self.workflow_dict[(self.workflow_dict.NGsBlkXp>self.PW_G[-len(converged)])]['NGsBlkXp'].values[:])
                
                l = len(oversteps_Ry)
                converged_result = self.b_energy_Ry[-l]
            else: 
                if hasattr(self,'PW_G'): # do this only for a given PW cutoff. if only diagonal (not implemented yet), do normal 
                    condition = (self.real.NGsBlkXp==self.PW_G[-1]) & (abs((self.real[what]-self.real[what].values[-1])/self.real[what].values[-1])<=conv_thr) 
                    if self.conv_thr_units == 'eV': condition = (self.real.NGsBlkXp==self.PW_G[-1]) & (abs((self.real[what]-self.real[what].values[-1]))<=conv_thr) 
                    #oversteps = list(self.real[condition].uuid)[-len(converged)+1:] #  [-len(converged)+1:]
                else:
                    condition = abs((self.real[what]-self.real[what].values[-1])/self.real[what].values[-1])<=conv_thr
                    if self.conv_thr_units == 'eV': condition = abs((self.real[what]-self.real[what].values[-1]))<=conv_thr
                
                if len(converged) >= self.iter*self.steps + 1 and not hasattr(self,'PW_G'):
                    oversteps= list(self.real[condition].uuid)[-(self.iter*self.steps):]  #converged[:-1]
                elif len(converged) >= self.iter*self.steps and hasattr(self,'PW_G'):
                    oversteps= list(self.real[condition].uuid)[-(self.iter*self.steps)+1:]  #converged[:-1]
                #elif self.convergence_algorithm == 'newton_1D': 
                #    oversteps= list(self.real[condition].uuid)[-(self.iter*self.steps)+1:]  #converged[:-1]
                else:
                    oversteps= list(self.real[condition].uuid)[-len(converged)+1:]  #converged[:-1]


                if hasattr(self,'PW_G'):
                    if len(oversteps) >= len(list(self.real[self.real.NGsBlkXp==self.PW_G[-1]].uuid)): oversteps = list(self.real[self.real.NGsBlkXp==self.PW_G[-1]].uuid)[1:]

                l = len(oversteps)
                converged_result = self.conv_array[what][-l]
                
                #if self.convergence_algorithm == 'newton_1D': 
                #    oversteps = list(set(oversteps[1:]))
                #    converged = list(set(converged[1:]))
                #    self.converged = list(set(self.converged[1:]))
                
        
        hint={}
        for i in self.var:
            if not ratio: hint[i] = self.p[self.var.index(i),-len(oversteps)]


        if ratio: self.oversteps = oversteps
        
        return self.delta_, is_converged, oversteps, converged_result, hint
            
    def newton_1D(self, what, evaluation='fit',ratio=False,diagonal=False): #'numerical'/'fit'
        perr = 10
        if self.functional_form == 'power_law':
            powers = [1,2,3]
        elif self.functional_form == 'exponential':
            powers = [1]
        elif self.functional_form == 'log':
            powers = [1]
        
        if ratio:
            homo = self.b_energy_Ry[-self.steps:]
            params= self.PW_G[-self.steps:]
            last= self.PW_G[-1]
            delta = self.delta[-1]
            if len(params)<3: return False, None
        elif diagonal:
            homo = self.quantity[-self.steps:]
            params= self.PW_G[-self.steps:]
            last= self.PW_G[-1]
            delta = self.delta[-1]
            if len(params)<3: return False, None
        else:
            homo = self.conv_array[what][-self.steps:]
            params=self.p[0,-self.steps:]
            last=self.p[0,-1]
            delta = self.delta[0]
        
        for i in powers:
            if self.functional_form == 'power_law':
                f = lambda x,a,b: a/x**i + b
            elif self.functional_form == 'exponential':
                f = lambda x,a,b: np.exp(a*x) + b 
            elif self.functional_form == 'log':
                f = lambda x,a,b: np.log(1+a/x) + b 
            try:
                popt,pcov = optimize.curve_fit(f,
                                           xdata=params,  
                                           ydata=homo,
                                           sigma=1/(params))

                perr_n = abs(np.average(f(params,*popt)-homo,))
                #print(perr_n,perr_n < perr)
                if perr_n < perr:
                    candidates = i
                    perr = perr_n
            except:
                pass
        
        if self.functional_form == 'power_law':
            f = lambda x,a,b: a/x**candidates + b
            fx = lambda x,a,b: -candidates*a/x**(candidates+1)
            fxx = lambda x,a,b: candidates*(candidates+1)*a/x**(candidates+2) 
        elif self.functional_form == 'exponential':
            f = lambda x,a,b: np.exp(a*x)  + b
            fx = lambda x,a,b: a*np.exp(a*x) 
            fxx = lambda x,a,b: a*a*np.exp(a*x)      
        elif self.functional_form == 'log':
            f = lambda x,a,b: np.log(1+a/x) + b 
            fx = lambda x,a,b: -a/(x*(x+a))
            fxx = lambda x,a,b: (2*a*x + a**2)/(x*(x+a))**2   
        
        popt,pcov = optimize.curve_fit(f,
                                       xdata=params,  
                                       ydata=homo,
                                       )

        self.extra = popt[-1]
        self.gradient = fx(last,*popt)
        self.laplacian = fxx(last,*popt)
        
        is_converged = abs((self.extra-homo[-1])/self.extra) < self.conv_thr*4 and abs((self.extra-homo[-2])/self.extra) < self.conv_thr*4
        if self.conv_thr_units == 'eV': is_converged = abs(self.extra-homo[-1]) < self.conv_thr*4 and abs(self.extra-homo[-2]) < self.conv_thr*4
        if ratio: is_converged = abs((self.extra-homo[-1])/homo[-1]) < 1e-1 and abs((self.extra-homo[-2])/homo[-2]) < 1e-1

        guess = last+abs(self.gradient/self.laplacian)
        #guess = last*(candidates+2)/(candidates+1) #analytic with power laws.
        if guess <= last : guess = last + 2*(delta)
        if guess > last + 2*(delta) : guess = last + delta
        if not isinstance(self.stop,list): self.stop = [self.stop]
        new_metrics = int((self.stop[0]-guess)/(self.conv_thr/abs(popt[0]))**(1/candidates)-guess)

        hint = {self.var[0]:guess,'extra':self.extra,'new_metrics':new_metrics,
                self.var[0]+'_fit_converged':abs(popt[0]/self.conv_thr)**(1/candidates),
                'power_law':candidates,'pop':False,'grad':self.gradient,'lapl':self.laplacian,'Newton_up':abs(self.gradient/self.laplacian)}
        
        if is_converged: hint['pop'] = True

        if ratio or diagonal:
            hint = {self.var[1]:guess,'extra_bands_Ry':self.extra,'new_metrics':new_metrics,
                self.var[0]+'_fit_converged':abs(popt[0]/self.conv_thr)**(1/candidates),
                'power_law':candidates,'ratio':abs((self.extra-homo[-1])/homo[-1]),'extra':self.extra,'bands_Ry':self.b_energy_Ry,'Ry':self.PW_G,
                'gaps':self.quantity,'bands_indexes':self.b_index,'delta':self.delta_,'converged_list':self.converged,'power':candidates}
        

        #if guess > self.stop[0]:
        hint.pop('new_metrics')
        hint.pop(self.var[0]+'_fit_converged')
        #hint.pop('power_law')

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
        if self.conv_thr_units != 'eV': homo = homo/homo[-1] 
        for eb in [1,2,3]:
            for eg in [1,2,3]:

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


        return abs(homo[-1]-popt[1]*popt[3])<self.conv_thr*5,infos #and concavity > 0 in the first boolean
    
    def analysis(self,): #also conv evaluation wrt the relative thr (0.01 on a 7 eV gap... not so important)
        
        is_converged_fit_b=False
        is_converged_fit_d=False
        is_converged_d=False
        is_converged_b=False
        hint_b=None
        hint_d=None
        hint={}
        hint_dummy={}

        if self.convergence_algorithm == 'no_one':
            return True and True, [], {}

        for i in self.quantities[:]:
            if 'newton_1D_ratio' in self.convergence_algorithm: self.ratio_evaluator(what=i)
            converged, is_converged, oversteps, converged_result, hint_dummy = self.dummy_convergence(what=i)
        
            if 'dummy' in self.convergence_algorithm:            
                #hint = None
                is_converged_fit = True #no fit
        
            elif 'newton_1D_ratio' in self.convergence_algorithm:
                is_converged_fit, hint = self.newton_1D(what=i)
                if is_converged_fit:
                    #try:
                    if self.ratio_evaluator(what=i):
                        converged_b, is_converged_b, oversteps_b, converged_result_b, hint_dummy_b = self.dummy_convergence(what=i,ratio=True)
                        #if is_converged_b:
                        is_converged_fit_b, hint_b = self.newton_1D(what=i,ratio=True)
                            #hint.update(hint_b)
                        converged_d, is_converged_d, oversteps_d, converged_result_d, hint_dummy_d = self.dummy_convergence(what=self.quantity,ratio=False,diagonal=True)
                        is_converged_fit_d, hint_d = self.newton_1D(what=self.quantity,diagonal=True)
                    #except:
                    #    pass
            elif 'newton_1D' in self.convergence_algorithm:
                is_converged_fit, hint = self.newton_1D(what=i)
        
            elif 'newton_2D_extra' in self.convergence_algorithm:
                finish = self.max_iterations == (self.iter)*(self.steps-self.skipped)
                if finish: 
                    if self.max_iterations > 4:
                        is_converged_fit, hint = self.newton_2D(what=i,extrapolation=True)
                    else:
                        pass
                
                hint.update(hint_dummy)
            
                is_converged, is_converged_fit, oversteps =  finish, finish, []
            
            elif 'newton_1D_extra' in self.convergence_algorithm:
                finish = self.max_iterations == (self.iter)*(self.steps-self.skipped)
                if finish: is_converged_fit, hint = self.newton_1D(what=i,extrapolation=True)
                hint.update(hint_dummy)
            
                is_converged, is_converged_fit, oversteps =  finish, finish, []
        
            elif 'newton_2D' in self.convergence_algorithm:
                is_converged_fit, hint = self.newton_2D(what=i)
        
            if is_converged and is_converged_fit:
                hint.update(hint_dummy)
                
                if 'newton_1D_ratio' in self.convergence_algorithm and not is_converged_d:  #(is_converged_b and is_converged_fit_b and is_converged_d): #is_converged_d: d is for full 2D convergence.....                   
                    if hint_b:
                        hint.update(hint_b)
                    else:
                        hint.pop('NGsBlkXp')
                    hint['converge_b_ratio'] = True
                elif is_converged_d:
                    oversteps = oversteps + oversteps_d
                
                hint['is_converged_diagonal'] = is_converged_d
                hint['is_converged_b'] = is_converged_b
                hint['is_converged_fit_b'] = is_converged_fit_b
                hint['is_converged_fit_d'] = is_converged_fit_d
                hint['hint_d'] = hint_d
                hint['converged'] = converged
                hint['self_p'] = self.p

                try:
                    hint['path_d'] = converged_d
                except:
                    pass
                #hint['hint_b'] = hint_b

            elif not is_converged or not is_converged_fit:
                if 'dummy' in self.convergence_algorithm:
                    hint = {} #this for k points... for now. I wnat Newton's also for meshes
                if 'newton_1D_ratio' in self.convergence_algorithm:
                    if 'NGsBlkXp' in hint.keys(): hint.pop('NGsBlkXp')
                break
           
        return is_converged and is_converged_fit, oversteps, hint
