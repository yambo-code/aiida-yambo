import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from collections import defaultdict
from aiida.orm.utils import DataFactory
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.work.run import run, submit, async
from aiida.work.workchain import WorkChain, while_, ToContext
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation
from aiida.orm.calculation.job.yambo  import YamboCalculation
from aiida.workflows.user.cnr_nano.yambo_utils import default_step_size, update_parameter_field, set_default_qp_param
from aiida.workflows.user.cnr_nano.yamborestart  import YamboRestartWf
from aiida.orm.data.remote import RemoteData
import numpy as np 
from scipy.optimize import  curve_fit 

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
PwProcess = PwCalculation.process()
YamboProcess = YamboCalculation.process()

"""
GW (Bands)
===========
First target parameters for convergences.
  - BndsRnXp   nbndX 
  - GbndRnge   nbndG
  - PPAPntXp [OK]
  - NGsBlkXp [OK] ecutX
  - FFTGvecs 

Target quantities for convergence:
  - GW band width along a single kpoint, between two band indexes

Test for convergence:
  - Change between runs smaller than threshold

possible techniques
  1. Coordinate descent
  2. k


#BSE (Optics)   *** THIS WILL WAIT FOR ITS OWN WORKFLOW******
#First target parameters for convergences.
#BSEBands

"""

class YamboConvergenceWorkflow(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        """
        as input we need
         1. variable
         2. threshold
         3. starting points
          converge_parameters = ['BndsRnXp','NGsBlkXp','GbndRnge']
          starting_points = [10,10,10]
        """
        super(YamboConvergenceWorkflow, cls).define(spec)
        spec.input("precode", valid_type=BaseType)
        spec.input("yambocode", valid_type=BaseType)
        spec.input("calculation_set", valid_type=ParameterData)
        spec.input("settings", valid_type=ParameterData)
        spec.input("parent_folder", valid_type=RemoteData)
        spec.input("parameters", valid_type=ParameterData, required=False,default=set_default_qp_param() )
        spec.input("converge_parameters", valid_type=List)
        spec.input("starting_points", valid_type=List)
        spec.input("default_step_size", valid_type=ParameterData,required=False,
                           default=DataFactory('parameter')(dict=default_step_size))
        spec.input("threshold", valid_type=Float, required=False, default=Float(0.1))

        spec.outline(
          cls.start,
          while_(cls.is_not_converged)(
              cls.run_next_update,
              ),
          cls.report
        )
        spec.dynamic_output()

    def init_parameters(self,paging):
        self.ctx.conv_elem = {}
        self.ctx.en_diffs =  []
        params = self.inputs.parameters.get_dict()
        for idx in range(len(self.inputs.converge_parameters)):
             starting_point = self.inputs.starting_points[idx] 
             field =  self.inputs.converge_parameters[idx] # PPAPntXp,...
             update_delta = np.ceil(self.inputs.default_step_size.get_dict()[field]*paging* starting_point )
             params[ field ] = update_parameter_field( field, starting_point, update_delta)
             if field in self.ctx.conv_elem:
                 self.ctx.conv_elem[field].append(params[field])
             else:
                 entry = []
                 entry.append(params[field])
                 self.ctx.conv_elem[field] = entry
        self.inputs.parameters = DataFactory('parameter')(dict= params)

    def start(self):
        outs={}
        for num in [0,1,2,3]: # includes 0 because of starting point
            self.init_parameters(num)
            outs[ 'r'+str(num) ] = async (YamboRestartWf,
                        precode= self.inputs.precode,
                        yambocode=self.inputs.yambocode,
                        parameters = self.inputs.parameters,
                        calculation_set= self.inputs.calculation_set,
                        parent_folder = self.inputs.parent_folder, settings = self.inputs.settings)
        return ToContext( **outs )

    def run_next_update(self):
        outs={}
        for num in [1,2,3,4]: # includes 0 because of starting point
            self.update_parameters(num)
            outs[ 'r'+str(num) ] = async (YamboRestartWf,
                        precode= self.inputs.precode,
                        yambocode=self.inputs.yambocode,
                        parameters = self.inputs.parameters,
                        calculation_set= self.inputs.calculation_set,
                        parent_folder = self.inputs.parent_folder, settings = self.inputs.settings)
        
        return ToContext(r0=outs['r1'] , r1=outs['r2']  , r2=outs['r3'] , r3=outs['r4']  )

    def update_parameters(self, paging):
        params = self.inputs.parameters.get_dict()
        starting_point = params [idx]
        for idx in range(len(self.inputs.converge_parameters)):
             field = self.inputs.converge_parameters[idx]
             update_delta = np.ceil( self.inputs.default_step_size.get_dict()[field]*paging*starting_point) 
             params[field] = update_parameter_field( field, params[field] ,  update_delta ) 
             self.ctx.conv_elem[field].append(params[field])
        self.inputs.parameters = DataFactory('parameter')(dict= params)


    def is_not_converged(self):
        r0_width = self.get_total_range(self.ctx.r0.out.gw.get_dict()['yambo_pk'])
        r1_width = self.get_total_range(self.ctx.r1.out.gw.get_dict()['yambo_pk'])
        r2_width = self.get_total_range(self.ctx.r2.out.gw.get_dict()['yambo_pk'])
        r3_width = self.get_total_range(self.ctx.r3.out.gw.get_dict()['yambo_pk'])
        self.ctx.en_diffs.extend([r0_width,r1_width,r2_width,r3_width])

        if len(self.ctx.en_diffs) > 16: # no more than 16 calcs
            return False
        if len(self.ctx.en_diffs) > 4:
            converged_fit = self.fitting_deviation(0) # only need to check against one convergence parameter at a time. 
            if  converged_fit:
                return False
            else:
                return True
        else:
            # check the the  differences are minimal, when on first 4 calculations
            delta =  abs(r0_width-r1_width) + abs(r1_width-r2_width) + abs(r2_width-r3_width)
            if delta < self.inputs.threshold:
                return False
            else:
                return True
        return True

    def fitting_deviation(self,idx):
        field = self.inputs.converge_parameters[idx]
        independent = np.array(self.ctx.conv_elem[field])
        dependent = np.array(self.ctx.en_diffs)
        if len(independent)> 4:
            def func(x,a,b):
                y=1.0
                y =y*(a/x+b)
                return y
            popt,pcov = curve_fit(func,independent[:-4],dependent[:-4])
            a,b = popt
            fit_data = func(independent, a,b)      
            deviations = np.abs(dependent[:4] - fit_data[:4])  # deviation of last four from extrapolated values at those points
            converged_fit = np.allclose(deviations, np.linspace(0.01,0.01, 4), atol=self.inputs.threshold) # last four are within 0.01 of predicted value
            return converged_fit
        return False

    def get_total_range(self,node_id):
        # CAVEAT: this does not calculate HOMO LUMO gap, but the width between two
        #         bands listed in the QPkrange, on the first kpoint selected,
        #         i.e. for 'QPkrange': [(1,16,30,31)] , will find width between 
        #         kpoint 1  band 30 and kpoint  1 band 31. 
        calc = load_node(node_id)
        table=calc.out.array_qp.get_array('qp_table')
        lowest_k = calc.inp.parameters.get_dict()['QPkrange'][0][0] # first kpoint listed, 
        lowest_b = calc.inp.parameters.get_dict()['QPkrange'][0][-2] # first band on first kpoint listed,
        highest_b = calc.inp.parameters.get_dict()['QPkrange'][0][-1]  # last band on first kpoint listed,
        argwlk = np.argwhere(table[:,0]==float(lowest_k))  # indexes for lowest kpoint
        argwlb = np.argwhere(table[:,1]==float(lowest_b))  # indexes for lowest band
        argwhb = np.argwhere(table[:,1]==float(highest_b)) # indexes for highest band
        arglb = np.intersect1d(argwlk,argwlb)              # index for lowest kpoints' lowest band
        arghb = np.intersect1d(argwlk,argwhb)              # index for lowest kpoint's highest band
        e_m_eo = calc.out.array_qp.get_array('E_minus_Eo') 
        eo = calc.out.array_qp.get_array('Eo')
        corrected = eo+e_m_eo
        corrected_lb = corrected[arglb]
        corrected_hb = corrected[arghb]
        return (corrected_hb- corrected_lb)[0]  # for spin polarized there will be two almost equivalent, else just one value.

    def report(self):
        """
        Output final quantities
        """
        from aiida.orm import DataFactory
        self.out("result", DataFactory('parameter')(dict={
            "parameters": self.inputs.parameters.get_dict(),
            "last_calc_pk": self.ctx.r0.out.gw.get_dict()['yambo_pk'],
            "convergence_space": self.ctx.conv_elem,
            "energy_widths":  self.ctx.en_diffs ,
            }))

if __name__ == "__main__":
    pass
