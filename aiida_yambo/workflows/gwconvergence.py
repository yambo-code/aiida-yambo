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
            self.inputs.calculation_set_pw = self.inputs.calculation_set  
        # if input calc has to be SCF not NSCF

    def start(self):
        # check that one of structure or parent_scf_calc have been provided.
        if 'parent_scf_folder' not in  self.inputs.keys() and 'structure' not in self.inputs.keys():
           raise InputValidationError("Either the structure or parent SCF calculation should be provided")
        
        self.init_parameters()
        #self.ctx.last_step = 'step_1_1'
        #self.ctx.step0_res = load_node(44846) 
        #self.ctx.step1_res = load_node(45050)
        #self.ctx.step2_res = load_node(45107)
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
        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
            return ToContext( step0_res =  self.step0_res_  ) 
        elif self.ctx.last_step == 'step_1_1' or self.ctx.last_step == 'step_1_2':
            return ToContext( step1_res =  self.step1_res_  ) 
        elif self.ctx.last_step == 'step_2_1' or self.ctx.last_step == 'step_2_2':
            return ToContext( step2_res =  self.step2_res_  ) 
        elif self.ctx.last_step == 'step_3_1' or self.ctx.last_step == 'step_3_2':
            return ToContext( step3_res =  self.step3_res_  ) 
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
        self.report("converging  FFTGvecs")
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_2_1':
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
        if self.ctx.last_step == 'step_0_1' and self.ctx.step_0_done== True:
             extra['parameters'] = ParameterData(dict=self.ctx.step0_res.out.convergence.get_dict()['parameters'] )
        convergence_parameters = DataFactory('parameter')(dict= { 
                                  'variable_to_converge': 'FFT_cutoff', 'conv_tol':0.1, 
                                   'start_value': 4 , 'step':2 , 'max_value': 60 })
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode ,
                        yambocode=self.inputs.yambocode ,
                        calculation_set= self.inputs.calculation_set ,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters, 
                        #converge_parameters= converge_parameters,
                        #parameters = self.ctx.step2_res["convergence"].get_dict()['parameters'],
                        #threshold = Float(0.01),starting_points = starting_points, 
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
        self.report ("Working on Bands Convergence ")
        nelec =  load_node(self.ctx.nscf_calc).out.output_parameters.get_dict()['number_of_electrons']
        band_cutoff  = int(nelec/2)
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_3_1':
             if self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] ==  1: # 1 == default, 
                 self.report(" converged cutt-off are similar to the default used in a previous band convergence, consistency achieved")
                 self.ctx.step_2_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             #band_cutoff = self.ctx.last_used_band ## BUG?
             band_cutoff = int(self.ctx.last_used_band *0.7)
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.report("updated the bands convegence parameters with cut-off from cutoff convergence step")
        if self.ctx.last_step == 'step_3_2':
             # CRUNCH TIME:  use  values from step3_2
             if self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] <=  self.ctx.last_used_cutoff : # 
                 # we are done, and consistent:
                 self.report(" converged cutt-off are similar to those used in a previous bands convergence, consistency achieved")
                 self.ctx.step_2_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             self.report("passing parameters from  converged cut-off, this can be repeated untill the two parameters are consistent ")
             #band_cutoff = self.ctx.last_used_band  ## BUG?
             band_cutoff = int( self.ctx.last_used_band*0.7) 
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.report("updated the bands convegence parameters with cut-off from cutoff convergence")
        if self.ctx.last_step != 'step_1_1' and self.ctx.last_step != 'step_1_2': # last iteration was W_cutoff not FFT  
             self.ctx.last_used_cutoff = self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp']
             self.report("Cut-off in last W-Cutoff convergence:  {}".format(self.ctx.last_used_cutoff)) 

        if self.ctx.last_step == 'step_1_1':
             params = self.ctx.step1_res.out.convergence.get_dict()['parameters'] 
             params['FFTGvecs'] =  2   # 
             params['NGsBlkXp'] =  2   # 
             extra['parameters'] = ParameterData(dict=params)
        convergence_parameters = DataFactory('parameter')(dict= { 
                                  'variable_to_converge': 'bands', 'conv_tol':0.1 ,
                                   'start_value': band_cutoff , 'step':1 , 'max_value': nelec -2  })
        self.report("converging  BndsRnXp, GbndRnge")
        p2y_result =submit (YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode,
                        yambocode=self.inputs.yambocode,
                        calculation_set= self.inputs.calculation_set,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters, 
                        #converge_parameters= converge_parameters,
                        #threshold = Float(0.01),starting_points = starting_points, 
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
        self.report ("Working on W-cutoff ")
        w_cutoff  = 1 
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_2_2':
             if self.ctx.last_used_band <= self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'][-1] :
                 self.report("bands input is similar to that used in a previous cut-off convergence, consistency achieved") 
                 self.ctx.step_3_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             self.report("passing parameters from  re-converged bands ")
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
             #w_cutoff =  self.ctx.last_used_cutoff  # start  from last used value. ## BUG?
             w_cutoff =  int(self.ctx.last_used_cutoff*0.7)  
        if self.ctx.last_step == 'step_2_1':
             self.report("passing parameters from  converged bands ")
             # use cut-off from 2_1
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
             #self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'][-1] 
        self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'][-1]
        self.report("Bands in last  bands convergence:  {}".format(self.ctx.last_used_band))
        convergence_parameters = DataFactory('parameter')(dict= { 
                                  'variable_to_converge': 'W_cutoff', 'conv_tol':0.1, 
                                   'start_value': w_cutoff , 'step': 1 , 'max_value':  20 }) 
        self.report("converging 1-D  W-off")
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode ,
                        yambocode=self.inputs.yambocode ,
                        calculation_set= self.inputs.calculation_set ,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters,   
                        #converge_parameters= converge_parameters,
                        #parameters = self.ctx.step2_res["convergence"].get_dict()['parameters'],
                        #threshold = Float(0.01),starting_points = starting_points, 
                        **extra
                        )
        self.report("Submitted  W-cut off Workflow  ")
        reslt = {}
        if not recheck :
            reslt['step3_1_res'] = p2y_result 
            self.ctx.last_step = 'step_3_1'
            self.ctx.first_runs3 = False 
        else:
            reslt['step3_2_res'] = p2y_result 
            self.ctx.last_step = 'step_3_2'
            self.ctx.step_3_done = True
            # if this  differs from that of step3_1_res 
        self.step3_res_ = p2y_result

    def step_0(self,recheck=False):
        self.report("Working on K-point convergence ")
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_1_1':
             extra['parameters'] = self.ctx.step1_res.out.convergence.get_dict()['parameters'] 

        self.report("converging K-points ")
        convergence_parameters = DataFactory('parameter')(dict= { 
                                  'variable_to_converge': 'kpoints', 'conv_tol':0.1, 
                                   'start_value': .9  , 'step':.1 , 'max_value': 0.017 })
                                   
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode,
                        yambocode=self.inputs.yambocode,
                        calculation_set= self.inputs.calculation_set,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters, 
                        #converge_parameters= converge_parameters,
                        #threshold = Float(0.01), starting_points = starting_points,
                        **extra
                        )
        self.report("Submitted the K-point convergence step ")
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
