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
from aiida_yambo.workflows.yambo_utils import default_convergence_settings
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.work.run import run, submit
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")

class YamboFullConvergenceWorkflow(WorkChain):
    """Full Convergence workflow will converge the direct gap at Gamma  w.r.t. Kpoints, FFT, Bands and G cutoff.

    This convergence workflow follows the following procedure,
    Starts by converging the kpoints, if an SCF calculation is passed in as input, the sCF step will be skipped,
    and computation will begin from the NSCF step, and the  K-point mesh will be varied for the NSCF computation
    that each used fr a yambo GW calculation. This is repeated untill convernence is achived. To optimize for 
    batch queuing systems, the workflow submits 4 different calculations at a time, each representing a full 
    NSCF-GW for a particular mesh size. After each 4 calculations the convergence tested and a decision to move
    to the next parameter or not. 

    After kpoints, the FFT grid is converged, using the k-point mesh from the first step, and similar to the kpoint
    convergence 4 individual GW calculations with different FFT grid sizes are submitted at once, and on completion,
    a test for convergence is performed. This step uses the  NSCF inputs from the converged k-point calculation.

    Following the FFT grid is the bands (BandsRnXP, GbandRnge), which similar to the FFT and kpoints, is performed with four submissions at a
    time followed by a convergence check, using converged k-points and FFT grid from the first two steps.

    Once the Bands converged, we converger the cuttoff for the greens function, which uses the converged parameters from
    the first three steps: k-points, FFT and the Bands. Similar to the preceeding steps,  four GW calculations with different values of cut-off
    are submitted, and convergence is tested. 

    After the cut-off, we redo the bands convergence step, and should the bands converge at a value greater than that from the first bands convergence,
    the cut-off convergence is repeated. This is repeated untill theres is consistency between the bands and cut-off.
    """

    @classmethod
    def define(cls, spec):
        """
        """
        super(YamboFullConvergenceWorkflow, cls).define(spec)

        spec.input("precode", valid_type=BaseType)
        spec.input("pwcode", valid_type=BaseType)
        spec.input("yambocode", valid_type=BaseType)
        spec.input("pseudo", valid_type=BaseType)
        spec.input("threshold", valid_type=Float, required=False, default=Float(0.1))
        spec.input("parent_scf_folder", valid_type=RemoteData, required=False)
        spec.input("structure", valid_type=StructureData,required=False)
        spec.input("calculation_set", valid_type=ParameterData)
        spec.input("calculation_set_pw", valid_type=ParameterData,required=False)
        spec.input("parameters", valid_type=ParameterData,required=False)
        spec.input("parameters_pw", valid_type=ParameterData,required=False)
        spec.input("parameters_pw_nscf", valid_type=ParameterData,required=False)
        spec.input("convergence_settings", valid_type=ParameterData,required=False)
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
        if 'convergence_settings' in self.inputs.keys():
            self.ctx.convergence_settings = self.inputs.convergence_settings
        else:
            self.ctx.convergence_settings = default_convergence_settings()

    def start(self):
        # check that one of structure or parent_scf_calc have been provided.
        if 'parent_scf_folder' not in  self.inputs.keys() and 'structure' not in self.inputs.keys():
           raise InputValidationError("Either the structure or parent SCF calculation should be provided")
        self.ctx.ordered_outputs = [] 
        self.init_parameters()

        """ DEBUG USE ONLY.
        self.ctx.last_step = 'step_1_1'       # select the step  you want to start AFTER.
        self.ctx.step0_res = load_node(37562)  # Fill nodes for prior convergence for all steps you want to skip
        self.ctx.step1_res = load_node(37778)  # "" ""
        self.ctx.step2_res = load_node(45107) # "" ""
        self.ctx.first_run = False            # ""  ""
        self.ctx.scf_calc = self.ctx.step0_res.out.convergence.get_dict()["scf_pk"]     #  ""  "" 
        self.ctx.nscf_calc = self.ctx.step0_res.out.convergence.get_dict()["nscf_pk"]   #  ""  ""
        """
  
    def run_next_update(self):
        """This function will run at each iteration and call the right step depending on what step came before.

        iThe steps are
        step_0 : k-point convergence
        step_1 : FFT convergence
        step_2 : Bands covergence
        step_3 : cutoff convergence
        Each will be called one at a time untill convergence is achieved. 
        See the class `Docstring` to get a description of the algorithm.
        """

        if self.ctx.first_run:
            self.step_0()
        elif self.ctx.last_step == 'step_0_1':
            # Run kpoint  starting with  coarse K-point grid, treat as independent of the rest of the parameters
            self.step_1()
        elif self.ctx.last_step == 'step_1_1':
            # Run FFT from a  coarse FFT grid,  treat as independent, though use converged k-points
            self.step_2()
        elif self.ctx.last_step == 'step_2_1':
            # Run Bands  with  convergged FFT and kpoints
            self.step_3()
        elif self.ctx.last_step == 'step_3_1':
            # Run  G cut-off convergence with converged bands, FFT, kpoints, if different from defaults, else
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
        """This function is in the spec.cls,  and is used to resolve the `future` object  and store it in a `self.ctx` variable after each iteration.

        This function will receive the future object stored in a ctx variable by functions that are not in the  spec.cls and can not therefore 
        resolve the `future`  i.e. call `ToContext` on a `future`. These functions will store the subworkflow's  future in the context  and here will
        resolve it and wait for the result by calling ToContext, storing the result in a context variable, which is selected depending on which
        step the  subworkflow represent.

        """
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
        """Here we store the ordered convergece , SCF and NSCF calcs in the `stx` to keep it available for subsequent calculations that need them, and prevent repetition

        We store the scf and nscf calcs after kpoint convergence, as well as the convergence data after each convergence step in an ordere array to keep
        track of how the workflow evolves to convergence.
        We have to be carefull not to double add the bands/W_cutoff at the end, which ever is the last
        """
        self.report(" persisting outputs to context ")
        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
            self.ctx.scf_calc = self.ctx.step0_res.out.convergence.get_dict()["scf_pk"]
            self.ctx.nscf_calc = self.ctx.step0_res.out.convergence.get_dict()["nscf_pk"]
            self.report("persisted nscf calc to be used as parent.")

        if self.ctx.bands_n_cutoff_consistent:
            return # dont double append thins once the full convergence is done 

        if self.ctx.last_step == 'step_0_1' or self.ctx.last_step == 'step_0_2':
           self.ctx.ordered_outputs.append( self.ctx.step0_res.out.convergence.get_dict() )
        elif self.ctx.last_step == 'step_1_1' or self.ctx.last_step == 'step_1_2':
           self.ctx.ordered_outputs.append( self.ctx.step1_res.out.convergence.get_dict() )
        elif self.ctx.last_step == 'step_2_1' or self.ctx.last_step == 'step_2_2': # store last conve
           self.ctx.ordered_outputs.append( self.ctx.step2_res.out.convergence.get_dict() )
        elif self.ctx.last_step == 'step_3_1' or  self.ctx.last_step == 'step_3_2':
           self.ctx.ordered_outputs.append( self.ctx.step3_res.out.convergence.get_dict() )
        

    def step_1(self, recheck=False):
        """This calls the YamboConvergenceWorkflow as a subworkflow, converging the FFT grid.

        We converge the FFT grid,  using the converged kpoints from  a preceeding kpoints
        convergence calculation. This is  a 1-D convergence performed by a subworkflow.
        """

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
                                  'variable_to_converge': 'FFT_cutoff', 'conv_tol':float(self.inputs.threshold), 
                                  'start_value': self.ctx.convergence_settings.dict.start_fft , 'step':20 , # 50
                                  'max_value': self.ctx.convergence_settings.dict.max_fft }) # max 400
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode ,
                        yambocode=self.inputs.yambocode ,
                        calculation_set= self.inputs.calculation_set ,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        parent_nscf_folder = load_node(self.ctx.nscf_calc).out.remote_folder, 
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters, 
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
        """This calls the YamboConvergenceWorkflow as a subworkflow, converging the  Bands.

        We converge the Bands,  using the converged kpoints from  a preceeding kpoints,
        converged FFT from a preceeding FFT convergence.
        This is  a 1-D convergence performed by a subworkflow.
        """
        self.report ("Working on Bands Convergence ")
        nelec =  load_node(self.ctx.nscf_calc).out.output_parameters.get_dict()['number_of_electrons']
        nbands = load_node(self.ctx.nscf_calc).out.output_parameters.get_dict()['number_of_bands']
        self.ctx.MAX_B_VAL = self.ctx.convergence_settings.dict.max_bands #   int(nelec*8) 
        band_cutoff  = self.ctx.convergence_settings.dict.start_bands #  min(nelec,nbands)
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_3_1':
             if self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'] == self.ctx.convergence_settings.dict.start_w_cutoff  : # 1 == default
                 self.report(" converged cutt-off are similar to the default used in a previous band convergence, consistency achieved")
                 self.ctx.step_2_done = True
                 self.ctx.bands_n_cutoff_consistent = True
                 return 
             #band_cutoff = int(self.ctx.last_used_band *0.7)
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.report("updated the bands convergence parameters with cut-off from cutoff convergence step")
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
             #band_cutoff = int( self.ctx.last_used_band*0.7) 
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
             self.report("updated the bands convegence parameters with cut-off from cutoff convergence")
        if self.ctx.last_step != 'step_1_1' and self.ctx.last_step != 'step_1_2': # last iteration was W_cutoff not FFT  
             self.ctx.last_used_cutoff = self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp']
             self.report("Cut-off in last W-Cutoff convergence:  {}".format(self.ctx.last_used_cutoff)) 

        if self.ctx.last_step == 'step_1_1':
             params = self.ctx.step1_res.out.convergence.get_dict()['parameters'] 
             extra['parameters'] = ParameterData(dict=params)
        convergence_parameters = DataFactory('parameter')(dict= { 
                                 'variable_to_converge': 'bands', 'conv_tol':float(self.inputs.threshold),
                                 'start_value': band_cutoff , 'step':10 , #band_cutoff
                                 'max_value': self.ctx.MAX_B_VAL  }) # self.ctx.MAX_B_VAL 
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
        """This calls the YamboConvergenceWorkflow as a subworkflow, converging the  G-cutoff.

        We converge the G-cutoff,  using the converged kpoints from  a preceeding kpoints,
        converged FFT from a preceeding FFT convergence and converged Bands from preceeding bands convergence
        This is  a 1-D convergence performed by a subworkflow.
        """
        nbands = load_node(self.ctx.nscf_calc).out.output_parameters.get_dict()['number_of_bands']
        self.report ("Working on W-cutoff ")
        w_cutoff = self.ctx.convergence_settings.dict.start_w_cutoff #2 
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
             #w_cutoff =  int(self.ctx.last_used_cutoff*0.7)  
             w_cutoff= int(self.ctx.step3_res.out.convergence.get_dict()['parameters']['NGsBlkXp'])
        if self.ctx.last_step == 'step_2_1':
             self.report("passing parameters from  converged bands ")
             # use cut-off from 2_1
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
             #self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'][-1] 
        self.ctx.last_used_band = self.ctx.step2_res.out.convergence.get_dict()['parameters']['BndsRnXp'][-1]
        self.report("Bands in last  bands convergence:  {}".format(self.ctx.last_used_band))
        convergence_parameters = DataFactory('parameter')(dict= { 
                                'variable_to_converge': 'W_cutoff', 'conv_tol':float(self.inputs.threshold), 
                                'start_value': w_cutoff , 'step': 1 ,# w_cutoff
                                'max_value': self.ctx.convergence_settings.dict.max_w_cutoff }) #self.ctx.MAX_B_VAL 
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
        """This calls the YamboConvergenceWorkflow as a subworkflow, converging the K-points.

        We converge the k-points by performing SCF and {NSCF+GW} at different mesh sizes untill convergence.
        This is  a 1-D convergence performed by a subworkflow.
        """
        self.report("Working on K-point convergence ")
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_1_1':
             extra['parameters'] = self.ctx.step1_res.out.convergence.get_dict()['parameters'] 
        if 'parameters' in self.inputs.keys():
             extra['parameters'] = self.inputs.parameters
        if 'parameters_pw' in self.inputs.keys():
             extra['parameters_pw'] = self.inputs.parameters_pw
        if 'parameters_pw_nscf' in  self.inputs.keys():
             extra['parameters_pw_nscf'] = self.inputs.parameters_pw_nscf
        self.report("converging K-points ")
        convergence_parameters = DataFactory('parameter')(dict= { 
                                  'variable_to_converge': 'kpoints', 'conv_tol':float(self.inputs.threshold), 
                                  'start_value': self.ctx.convergence_settings.dict.kpoint_starting_distance , 'step':.1, # IGNORE STEP 
                                   'max_value': self.ctx.convergence_settings.dict.kpoint_min_distance }) # 0.34 , 0.0250508117676 
                                   
        p2y_result = submit(YamboConvergenceWorkflow,
                        pwcode= self.inputs.pwcode,
                        precode= self.inputs.precode,
                        yambocode=self.inputs.yambocode,
                        calculation_set= self.inputs.calculation_set,
                        calculation_set_pw = self.inputs.calculation_set_pw,
                        pseudo = self.inputs.pseudo,
                        convergence_parameters = convergence_parameters, 
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
        """This function checks if all the individual convergence steps have  been marked as complete, 
           and decides whether the workflow should keep iterating with the next step or end calculations when convergence has been achieved."""

        # check we are not complete. 
        if self.ctx.step_0_done and self.ctx.step_1_done and self.ctx.step_2_done and self.ctx.step_3_done and self.ctx.bands_n_cutoff_consistent :
            self.report("convergence reached, workflow will stop")
            return False 
        else:
            self.report("No full  convergence achieved yet")
            self.report("progress:  kpoints converged: {}  , fft converged: {}  , bands converged: {}  ,  cut-off converged:{}".format(
                        self.ctx.step_0_done, self.ctx.step_1_done, self.ctx.step_2_done, self.ctx.step_3_done ))
            self.report("consistency for interdepended bands and cut-off: {}".format(self.ctx.bands_n_cutoff_consistent))
            return True 


    def report_wf(self):
        """Output final quantities"""
        from aiida.orm import DataFactory
        self.out("result", DataFactory('parameter')(dict={
             "kpoints": self.ctx.step0_res.out.convergence.get_dict(),
             "fft": self.ctx.step1_res.out.convergence.get_dict(),
             "bands": self.ctx.step2_res.out.convergence.get_dict(),
             "cutoff": self.ctx.step3_res.out.convergence.get_dict(),
             "ordered_step_output": self.ctx.ordered_outputs
            }))

if __name__ == "__main__":
    pass
