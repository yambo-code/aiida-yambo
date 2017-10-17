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
  - BndsRnXp   nbndX 
  - GbndRnge   nbndG
  - PPAPntXp [OK]
  - NGsBlkXp [OK] ecutX
  - FFTGvecs 
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
        self.ctx.step_1_done =False 
        self.ctx.step_2_done = False 
        self.ctx.step_3_done = False
        if 'parent_scf_folder' not in  self.inputs.keys(): 
            self.inputs.parent_scf_folder = False
        if 'structure' not in self.inputs.keys():
            self.inputs.structure = False
        if 'calculation_set_pw' not in self.inputs.keys():
            self.inputs.calculation_set_pw = self.inputs.calculation_set.copy()  
        # if input calc has to be SCF not NSCF
        self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow:  init_parameters done")

    def start(self):
        # check that one of structure or parent_scf_calc have been provided.
        if 'parent_scf_folder' not in  self.inputs.keys() and 'structure' not in self.inputs.keys():
            self.report("gwconvergence.pw:  start: ERROR: Either the structure or parent SCF calculation should be provided")
           raise InputValidationError("Either the structure or parent SCF calculation should be provided")
        
        self.init_parameters()
 
    def run_next_update(self):
        if self.ctx.first_run:
            # run NSCF, CONVERSION, converge kpoints.
            self.step_1()
        elif self.ctx.last_step == 'step_1_1':
            self.step_2()
            # decide whether we are at step 3, converge ecutX,
        elif self.ctx.last_step == 'step_2_1':
            self.step_3()
            # decide whether we are done with 3, redo 2
        elif self.ctx.last_step == 'step_3_1':
            self.step_2(f=True)
            # decide whehter we are done with 2, redo 1. 
        elif self.ctx.last_step == 'step_2_1':
            self.step_1(f=True)

        if self.ctx.first_run:
            self.ctx.first_run = False

    def keep_step_data(self):
        if self.ctx.last_step == 'step_1_1':
            self.ctx.scf_calc = self.ctx.step1_res.out.convergence.get_dict()["scf_pk"]
            self.ctx.nscf_calc = self.ctx.step1_res.out.convergence.get_dict()["nscf_pk"]

        elif self.ctx.last_step == 'step_2_1':
        elif self.ctx.last_step == 'step_3_1':
        elif self.ctx.last_step == 'step_2_1':



    def step_1(self,f=False):
        starting_points = List()
        starting_points.extend([16])
        converge_parameters = List()
        converge_parameters.extend(['kpoints'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_2_2':
             extra['parameters'] = self.ctx.step2_res["convergence"].get_dict()['parameters'] 

        self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow: step 1, converging K-points ")
        p2y_result =run(YamboConvergenceWorkflow,
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
        if self.ctx.first_run:
            self.ctx.step1_1_res = p2y_result 
            self.ctx.last_step = 'step_1_1'
        else:
            self.ctx.step1_2_res = p2y_result 
            self.ctx.last_step = 'step_1_2'
            self.ctx.step_2_done = True
        self.ctx.step1_res = p2y_result 
        self.ctx.first_run = False


    def step_2(self,f=False):
        starting_points = List()
        starting_points.extend([8,8])
        converge_parameters = List()
        converge_parameters.extend(['BndsRnXp','GbndRnge'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure
        if self.ctx.last_step == 'step_3_1':
             extra['parameters'] = ParameterData(dict=self.ctx.step3_res.out.convergence.get_dict()['parameters'] )
        if self.ctx.last_step == 'step_1_1':
             extra['parameters'] = ParameterData(dict=self.ctx.step1_res.out.convergence.get_dict()['parameters'] )
        self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow: step 2, converging  BndsRnXp, GbndRnge")
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

        if self.ctx.first_runs2:
            self.ctx.step2_1_res = p2y_result 
            self.ctx.last_step = 'step_2_1'
            self.ctx.first_runs2 = False 
        else:
            self.ctx.step2_2_res = p2y_result 
            self.ctx.last_step = 'step_2_2'
            self.ctx.step_2_done = True
        self.ctx.step2_res = p2y_result 

    def step_3(self,f=False):
        starting_points = List()
        starting_points.extend([16,16])
        converge_parameters = List()
        converge_parameters.extend(['NGsBlkXp'])
        extra={}
        if self.inputs.parent_scf_folder:
             extra['parent_scf_folder'] = self.inputs.parent_scf_folder
        if self.inputs.structure:
             extra['structure'] = self.inputs.structure.copy()
        if self.ctx.last_step == 'step_2_1':
             extra['parameters'] = ParameterData(dict=self.ctx.step2_res.out.convergence.get_dict()['parameters'] )
        self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow: step 3, converging  NGsBlkXp")
        p2y_result =run(YamboConvergenceWorkflow,
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

        if self.ctx.first_runs3:
            self.ctx.step3_1_res = p2y_result 
            self.ctx.last_step = 'step_3_1'
            self.ctx.first_runs3 = False 
        else:
            self.ctx.step3_2_res = p2y_result 
            self.ctx.last_step = 'step_3_2'
        self.ctx.step3_res = p2y_result 
        self.ctx.step_3_done = True

    def is_not_converged(self):
        # check we are not complete. 
        if self.ctx.step_1_done and self.ctx.step_2_done and self.ctx.step_3_done:
            self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow:  no convergence reached yet")
            return False 
        else:
            self.report("gwconvergence.pw:  YamboFullConvergenceWorkflow:  convergene achieved")
            return True 


    def report_wf(self):
        """
        Output final quantities
        """
        from aiida.orm import DataFactory
        self.out("result", DataFactory('parameter')(dict={
             "kpoints": self.ctx.step1_res.out.convergence.get_dict(),
             "BndsRnXp,GbndRnge": self.ctx.step2_res.out.convergence.get_dict(),
             "NGsBlkXp": self.ctx.step3_res.out.convergence.get_dict(),
            }))

if __name__ == "__main__":
    pass
