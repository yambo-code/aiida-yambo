import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.common.exceptions import InputValidationError,ValidationError, WorkflowInputValidationError
from aiida.orm import load_node
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.orm.data.remote import RemoteData
from aiida.common.exceptions import InputValidationError,ValidationError
from aiida.work.run import run, submit
from aiida.work.workchain import WorkChain, while_, ToContext
import numpy as np 
from scipy.optimize import  curve_fit 
from aiida_yambo.workflows.yamboconvergence  import  YamboConvergenceWorkflow
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.work.run import run, submit
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")

"""
GW (Bands)
===========
First target parameters for convergences.
  - BndsRnXp   nbndX \=-_
  - GbndRnge   nbndG /=-  Nocc -> Nocc..   Delta = .1%
  - PPAPntXp [OK] 
  - NGsBlkXp [OK]  ecutX  = 1-26 Ry  Delta=2
  - FFTGvecs [OK]  20 Ry -> 50 Ry  Delta = 2
  - Kpoints  2x2x2 -> XxXxX
  - Order: 
     FFT  => nbndX/nbndG => NGsBlkXp => Kpoints 
"""

class YamboFullConvergenceWorkflow(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        """
        STEP 1. Loop on Kpoints
        STEP 2. Loop on nbndX,nbndG
        STEP 3. Loop on ecutX

        Algorithm:
        =>  step 1
          => step 2  using converged from 1
            => step 3  using converged from 1, 2
            => step 2  using converged from 1,3
            => step 1  using converged from 2,3
        INPUTS:
         - SCF calc inputs/proper defaults.
         - structure. 
         - settings.
        """
        super(YamboFullConvergenceWorkflow, cls).define(spec)

        spec.input("precode", valid_type=BaseType)
        spec.input("pwcode", valid_type=BaseType)
        spec.input("yambocode", valid_type=BaseType)
        spec.input("pseudo", valid_type=BaseType)
        spec.input("parent_scf_folder", valid_type=RemoteData, required=False)
        spec.input("structure", valid_type=StructureData,required=False)
        spec.input("calculation_set", valid_type=ParameterData)
        spec.input("calculation_set_pw", valid_type=ParameterData,required=False)
        spec.outline(
          cls.start,
          while_(cls.is_not_converged)(
              cls.run_next_update,
              cls.contex_waits,
              cls.keep_step_data,
              ),
          cls.report_wf
        )
        spec.dynamic_output()

    def init_parameters(self):
        self.ctx.first_run = True
        self.ctx.first_runs2 = True
        self.ctx.first_runs3 = True
        self.ctx.last_step = ''
        self.ctx.step_0_done =False 
        self.ctx.step_1_done =False 
        self.ctx.step_2_done = False 
        self.ctx.step_3_done = False
        self.ctx.bands_n_cutoff_consistent = False
        if 'parent_scf_folder' not in  self.inputs.keys(): 
            self.inputs.parent_scf_folder = False
        if 'structure' not in self.inputs.keys():
            self.inputs.structure = False
        if 'calculation_set_pw' not in self.inputs.keys():
            self.inputs.calculation_set_pw = self.inputs.calculation_set.copy()  
        # if input calc has to be SCF not NSCF
        self.report(" init_parameters done")

    def start(self):
        # check that one of structure or parent_scf_calc have been provided.
        if 'parent_scf_folder' not in  self.inputs.keys() and 'structure' not in self.inputs.keys():
           self.report("ERROR: Either the structure or parent SCF calculation should be provided")
           raise InputValidationError("Either the structure or parent SCF calculation should be provided")
        
        self.init_parameters()
        #self.ctx.last_step = 'step_0_1'
        #self.ctx.step0_res = load_node(22963) 
        #self.ctx.first_run = False
        #self.ctx.scf_calc = self.ctx.step0_res.out.convergence.get_dict()["scf_pk"]
        #self.ctx.nscf_calc = self.ctx.step0_res.out.convergence.get_dict()["nscf_pk"]
  
    def run_next_update(self):
        # step 0 == kpoints
        # step 1 ==  FFT
        # step 2 == bands
        # step 3 == cut-off
        if self.ctx.first_run:
            self.step_0()
        elif self.ctx.last_step == 'step_0_1':
            # Run with  coarse K-point grid, treat as independent
            self.step_1()
        elif self.ctx.last_step == 'step_1_1':
            # Run with  coarse FFT grid,  treat as independent
            self.step_2()
        elif self.ctx.last_step == 'step_2_1':
            # Run with  step_2 converged values. 
            self.step_3()
        elif self.ctx.last_step == 'step_3_1':
            # Run with step 3_1 converged values, if different from defaults, else
            # convergence is done 
            self.step_2(recheck=True)
        elif self.ctx.last_step == 'step_2_2':
            # we need to call step_3_2, check if the new converged  bands input value  is
            # different from that used  step_3_1 if so  submit and update last used input
            # else mark self.ctx.bands_n_cutoff_consistent
            # as true
            self.step_3(recheck=True)
        elif self.ctx.last_step == 'step_3_2':
            # We need to call step_2_2 check if the new converged cut-off input value is different
            # from  that of step_3_1, if different, 
            self.step_2(recheck=True)

        if self.ctx.first_run:
            self.ctx.first_run = False

    def contex_waits(self):
        self.report("last calc {}".format(self.ctx.last_step))
        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
            return ToContext( step0_res =  self.step0_res_  ) 
        elif self.ctx.last_step == 'step_1_1' or self.ctx.last_step == 'step_1_2':
            return ToContext( step1_res =  self.step1_res_  ) 
        elif self.ctx.last_step == 'step_2_1' or self.ctx.last_step == 'step_2_2':
            return ToContext( step2_res =  self.step2_res_  ) 
        elif self.ctx.last_step == 'step_3_1' or self.ctx.last_step == 'step_3_2':
            return ToContext( step3_res =  self.step3_res_  ) 
        self.report ("no contex waits ")
        return 

    def keep_step_data(self):
        self.report(" persisting outputs to context ")
        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
            self.ctx.scf_calc = self.ctx.step0_res.out.convergence.get_dict()["scf_pk"]
            self.ctx.nscf_calc = self.ctx.step0_res.out.convergence.get_dict()["nscf_pk"]
            self.report("persisted nscf calc to be used as parent.")

        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
           pass
        elif self.ctx.last_step == 'step_1_1' or self.ctx.last_step == 'step_1_2':
           self.report("stepq_res  {}".format(self.ctx.step1_res.out))
           pass
        elif self.ctx.last_step == 'step_2_1': # store last conve
           pass
        elif self.ctx.last_step == 'step_2_2':
           pass
        elif self.ctx.last_step == 'step_3_1':
           pass
        elif self.ctx.last_step == 'step_3_2':
           pass
        

    def step_1(self, recheck=False):
        starting_points = List()
        starting_points.extend([20])
        converge_parameters = List()
        converge_parameters.extend(['FFTGvecs'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure.copy()
        if self.ctx.last_step == 'step_2_1':
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
        self.report("converging  FFTGvecs")
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode.copy(),
                        precode= self.inputs.precode.copy() ,
                        yambocode=self.inputs.yambocode.copy() ,
                        calculation_set= self.inputs.calculation_set.copy() ,
                        calculation_set_pw = self.inputs.calculation_set_pw.copy(),
                        converge_parameters= converge_parameters,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo.copy(),
                        #parameters = self.ctx.step2_res["convergence"].get_dict()['parameters'],
                        threshold = Float(0.01),starting_points = starting_points, 
                        **extra
                        )
        self.report ("submitted 1-D FFT convergence workflow")
        reslt = {}
        if not recheck :
            reslt['step1_1_res'] = p2y_result 
            self.ctx.last_step = 'step_1_1'
            self.ctx.first_runs1 = False 
            self.ctx.step_1_done = True
        else:
            reslt['step1_2_res'] = p2y_result 
            self.ctx.last_step = 'step_1_2'
         
        self.step1_res_  = p2y_result

    def step_2(self,recheck=False):
        nelec =  load_node(self.ctx.nscf_calc).out.output_parameters.get_dict()['number_of_electrons']
        starting_points = List()
        starting_points.extend([ int(nelec/2) , int(nelec/2) ])
        converge_parameters = List()
        converge_parameters.extend(['BndsRnXp','GbndRnge'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_3_1':
             self.report(" cutoff from preceeding cut-off convergence  {}, default {}".format(
                       self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'], 1 ))
             if self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] ==  1: # 1 == default, 
                 self.report(" converged cutt-off are similar to the default used in a previous band convergence, consistency achieved")
                 self.ctx.step_2_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'] 
             starting_points = List()
             starting_points.extend([used_band, used_band])
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.ctx.last_used_cutoff = self.ctx.step3_res.out.convergence.get_dict()['parameters']['BndsRnXp'] 
             self.report("updated the bands convegence parameters with cut-off from cutoff convergence")
        if self.ctx.last_step == 'step_3_2':
             # CRUNCH TIME:  use  values from step3_2
             self.report("passing parameters from  converged cut-off ")
             self.report("cutoff from preceeding cut-off convergence {}, self.ctx.last_used_cutoff {}".format(
                           self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'],
                           self.ctx.last_used_cutoff))
             if self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] ==  self.ctx.last_used_cutoff : # 
                 # we are done, and consistent:
                 self.report(" converged cutt-off are similar to those used in a previous bands convergence, consistency achieved")
                 self.ctx.step_2_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'] 
             starting_points = List()
             starting_points.extend([used_band, used_band])
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.ctx.last_used_cutoff = self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] 
             self.report("updated the bands convegence parameters with cut-off from cutoff convergence")
        if self.ctx.last_step == 'step_1_1':
             self.report ("passing parameters from converged FFT")
             extra['parameters'] = ParameterData(dict=self.ctx.step1_res.out.convergence.get_dict()['parameters'] )
             #self.ctx.last_used_band =  
        self.report("converging  BndsRnXp, GbndRnge")
        p2y_result =submit (YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode.copy(),
                        precode= self.inputs.precode.copy(),
                        yambocode=self.inputs.yambocode.copy(),
                        calculation_set= self.inputs.calculation_set.copy(),
                        calculation_set_pw = self.inputs.calculation_set_pw.copy(),
                        converge_parameters= converge_parameters,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo.copy(),
                        threshold = Float(0.01),starting_points = starting_points, 
                        **extra
                        )
        self.report ("submitted 1-D bands convergence workflow")
        reslt = {}
        if not recheck:
            step2_1_res = p2y_result 
            self.ctx.last_step = 'step_2_1'
            self.ctx.first_runs2 = False 
        else:
            self.step2_2_res = p2y_result 
            self.ctx.last_step = 'step_2_2'
            self.ctx.step_2_done = True
        self.step2_res_ = p2y_result

    def step_3(self, recheck=False):
        starting_points = List()
        starting_points.extend([1])
        converge_parameters = List()
        converge_parameters.extend(['NGsBlkXp'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure.copy()
        if self.ctx.last_step == 'step_2_2':
             self.report("passing parameters from  re-converged bands ")
             # use cut-off from 2_2
             self.report("converged bands from preceeding convergence: {}, self.ctx.last_used_band {} ".format(
                          self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'], self.ctx.last_used_band))
             if self.ctx.last_used_band == self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'] :
                 self.report("bands input is similar to that used in a previous cut-off convergence, consistency achieved") 
                 self.ctx.step_3_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
             self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'] 
        if self.ctx.last_step == 'step_2_1':
             self.report("passing parameters from  converged bands ")
             # use cut-off from 2_1
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
             self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'] 
        self.report("converging 1-D  Cut-off")
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode.copy(),
                        precode= self.inputs.precode.copy() ,
                        yambocode=self.inputs.yambocode.copy() ,
                        calculation_set= self.inputs.calculation_set.copy() ,
                        calculation_set_pw = self.inputs.calculation_set_pw.copy(),
                        converge_parameters= converge_parameters,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo.copy(),
                        #parameters = self.ctx.step2_res["convergence"].get_dict()['parameters'],
                        threshold = Float(0.01),starting_points = starting_points, 
                        **extra
                        )
        self.report("converging  cut-off ")
        reslt = {}
        if not recheck :
            reslt['step3_1_res'] = p2y_result 
            self.ctx.last_step = 'step_3_1'
            self.ctx.first_runs3 = False 
        else:
            reslt['step3_2_res'] = p2y_result 
            self.ctx.last_step = 'step_3_2'
            self.ctx.step_3_done = True
            # if this  differes from that of step3_1_res 
        self.step3_res_ = p2y_result

    def step_0(self,recheck=False):
        starting_points = List()
        starting_points.extend([.2])
        converge_parameters = List()
        converge_parameters.extend(['kpoints'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_1_1':
             extra['parameters'] = self.ctx.step1_res.out.convergence.get_dict()['parameters'] 

        self.report("converging K-points ")
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode.copy(),
                        precode= self.inputs.precode.copy(),
                        yambocode=self.inputs.yambocode.copy(),
                        calculation_set= self.inputs.calculation_set.copy(),
                        calculation_set_pw = self.inputs.calculation_set_pw.copy(),
                        converge_parameters= converge_parameters,
                        pseudo = self.inputs.pseudo.copy(),
                        threshold = Float(0.01), starting_points = starting_points,
                        **extra
                        )
        reslt = {}
        if not recheck:
            reslt ['step0_1_res'] = p2y_result 
            self.ctx.last_step = 'step_0_1'
            self.ctx.step_0_done = True
        else:
            reslt ['step0_2_res'] = p2y_result 
            self.ctx.last_step = 'step_0_2'
        self.step0_res_ = p2y_result 
        self.ctx.first_run = False
        

    def is_not_converged(self):
        # check we are not complete. 
        if self.ctx.step_0_done and self.ctx.step_1_done and self.ctx.step_2_done and self.ctx.step_3_done and self.ctx.bands_n_cutoff_consistent :
            self.report("convergence reached, workflow will stop")
            return False 
        else:
            self.report("no  convergene achieved")
            self.report("progress:  kpoints converged: ")
            self.report("progress:  kpoints converged: {}  , fft converged: {}  , bands converged: {}  ,  cut-off converged:{}".format(
                        self.ctx.step_0_done, self.ctx.step_1_done, self.ctx.step_2_done, self.ctx.step_3_done ))
            self.report("progress: consistency for interdepended bands and cut-off  {}".format(self.ctx.bands_n_cutoff_consistent))
            return True 


    def report_wf(self):
        """
        Output final quantities
        """
        from aiida.orm import DataFactory
        self.out("result", DataFactory('parameter')(dict={
             "kpoints": self.ctx.step0_res.out.convergence.get_dict(),
             "fft": self.ctx.step1_res.out.convergence.get_dict(),
             "bands": self.ctx.step2_res.out.convergence.get_dict(),
             "cutoff": self.ctx.step3_res.out.convergence.get_dict(),
            }))

if __name__ == "__main__":
    pass
