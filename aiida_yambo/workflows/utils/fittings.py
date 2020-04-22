import numpy as np
from scipy.optimize import curve_fit

'''
author: Andrea Ferretti
'''

def func(xv,*args):
   y = 1.0
   for i in range(len(xv)):
      A=args[2*i]
      B=args[2*i+1]
      xval=xv[i]
      y = y * ( A/xval + B)
   return y

def fitting(func, xdata,ydata, p0=None,method=None,weights=None):
   #
   if (p0==None):
      nvars=len(xdata)
      p0=[1.0 for x in range(2*nvars)]
   #
   try:
      params, pcov = curve_fit(func,xdata,ydata,p0=p0,method=None,sigma=weights)
   except ValueError:
      print("ValueError: Invalid input data")
      info=-1
   except RuntimeError:
      print("RuntimeError: LeastSquares fitting failed")
      info=-2
   except:
      print("Unexpected error")
      info=-3
   else:
      info=pcov.trace()
   #
   val_inf = 1.0
   for i in range(0,len(params),2):
      val_inf=val_inf*params[i+1]
   #
   rms=np.mean((ydata-func(xdata, *params))**2)
   #
   print("Fitting PARAMS: ",params)
   print("Fitting   RMS : ",rms)
   print("Fitting EXTRAP: ",val_inf)
   
   return params, rms, val_inf

def load_data(filename,n_set):
   import numpy as np
   data=np.loadtxt(filename,comments="#")
   ncol=data.shape[1]
   xdata=[]
   for i in range(ncol-nset):
     xdata.append(data[:,i])
   ydata=data[:,ncol-nset:]
   #
   return xdata,ydata