class Convergence_evaluator(): 
    
    def __init__(self, **kwargs): #lista_YamboIn, conv_array, parametri_da_conv(se lista fai fit multidimens), thr, window
        for k,v in kwargs.items():
            setattr(self, k, v)
        self.hint = {}
        self.extrapolated = 1
        if not hasattr(self,'power_law'): self.power_law = 1 
        
        self.p = []
        for param in self.parameters:
            self.p.append(self.p_val[param][-self.steps:])
        
        self.p = np.array(self.p)
            
    def dummy_convergence(self): #solo window, thr e oversteps
        self.delta = self.conv_array[-self.steps:]-self.conv_array[-1]
        converged = self.delta[-self.window:][np.where(abs(self.delta[-self.window:])<=self.thr)]
        if len(converged)<self.window:
            is_converged = False
            oversteps = 0
            converged_result = None
        else:
            is_converged = True
            oversteps = len(converged)
            for overstep in range(self.window+1,len(self.delta)+1):
                overconverged = self.delta[-overstep:][np.where(abs(self.delta[-overstep:])<=self.thr)]
                if oversteps < len(overconverged):
                    oversteps = len(overconverged)
                else:
                    break     
            converged_result = self.conv_array[-oversteps]
            
        return self.conv_array[-self.steps:], self.delta, converged, is_converged, oversteps-1, converged_result
    
    def convergence_function(self,xv,*args): #con fit e previsione parametri a convergenza con la thr
        if isinstance(self.power_law,int): self.power_law = [self.power_law]*len(self.parameters)
        y = 1.0
        for i in range(len(xv)):
            A=args[2*i]
            B=args[2*i+1]
            xval=xv[i]
            y = y * ( A/xval + B)
        return y
    
    def fit_prediction(self):  #1D

        sig = self.p[0,:]
        for i in range(1,len(self.p)):
            sig = sig*self.p[i,:]
        sig = sig[-self.steps_fit:]
        extra, pcov = curve_fit(self.convergence_function,self.p[:,-self.steps_fit:],self.delta[-self.steps_fit:],p0=[1,1]*len(self.parameters),sigma=1/sig)
        self.extra = extra
        print(extra)
        hints = {}
        for i in range(len(self.parameters)):
            a = extra[2*i]
            b = extra[2*i+1]
            self.extrapolated = b*self.extrapolated
            f = lambda x: a/x**self.power_law[i]
            x_1 = a/self.thr
            x_2 = np.sqrt(abs(a)/self.thr)
            delta_ = self.p[i,-1] - self.p[i,-2]
            print(delta_)
            delta_1 = x_1 - self.p[i,-1]
            delta_2 = x_2 - self.p[i,-1]
            
            
            alpha = delta_ #/ b
            beta = delta_**2 #/ b
            gamma = delta_**3 #/ b
            
            grad_hint = abs(abs(x_1)/self.p[i,-1]-1)
                      
            hint = np.sqrt(grad_hint/delta_)

            if self.logic == 'aggressive': hint = hint**2
            if self.has_ratio: hint = grad_hint/self.p[i,-1] + 1

            hints[self.parameters[i]] = hint
        
        return hints

    def numerical_gradients(self):
        
        #matrix or ...?
        self.delta_x = self.p[-1,-self.steps_fit:]-self.p[i,-self.steps_fit:]
        for i in range(len(self.parameters)):
            #num_grad = self.delta[-self.steps_fit:]*(1/self.delta_x[i,-self.steps_fit:])
            num_grad = np.gradient(self.delta[-self.steps_fit:],self.p[i,-self.steps_fit:])
        