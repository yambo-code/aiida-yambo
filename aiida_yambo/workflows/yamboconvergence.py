import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from aiida.common.exceptions import InputValidationError,ValidationError
from collections import defaultdict
from aiida.orm.utils import DataFactory, CalculationFactory
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List, Bool
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.work.run import run, submit
from aiida.work.workchain import WorkChain, while_, ToContext, Outputs
from aiida_yambo.calculations.gw  import YamboCalculation
from aiida.common.links import LinkType
from aiida_yambo.workflows.yambo_utils import default_step_size, update_parameter_field, set_default_qp_param,\
               default_pw_settings, set_default_pw_param, yambo_default_settings, default_qpkrange,\
               p2y_default_settings, is_converged
from aiida_yambo.workflows.yamborestart  import YamboRestartWf
from aiida_yambo.workflows.yambowf  import YamboWorkflow
from aiida.orm.data.remote import RemoteData
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_yambo.calculations.gw  import YamboCalculation
import numpy as np 
from scipy.optimize import  curve_fit 

#PwCalculation = CalculationFactory('quantumespresso.pw')
#YamboCalculation = CalculationFactory('yambo.yambo')

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
  - kpoints

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
        
        convergence_parameters = {'variable_to_converge':'bands' or 'W_cutoff' or 'kpoints' or 'FFT_cutoff',
                                    'start_value': 10,
                                    'step': 5,
                                    'max_value':100,
                                    'conv_tol': 0.1,
                                    'conv_window': 3 (optional),
                                    'loop_length': 4 (optional),
                                    }
        """
        super(YamboConvergenceWorkflow, cls).define(spec)
        spec.input("precode", valid_type=BaseType)
        spec.input("pwcode", valid_type=BaseType, required=False)
        spec.input("yambocode", valid_type=BaseType)
        spec.input("pseudo", valid_type=BaseType,required=True)
        spec.input("calculation_set_pw", valid_type=ParameterData, required=False)
        spec.input("calculation_set_p2y", valid_type=ParameterData,required=False)
        spec.input("calculation_set", valid_type=ParameterData )
        spec.input("parent_scf_folder", valid_type=RemoteData, required=False)
        spec.input("settings_p2y", valid_type=ParameterData, required=False, default = p2y_default_settings())
        spec.input("settings", valid_type=ParameterData, required=False, default = yambo_default_settings())
        spec.input("structure", valid_type=StructureData,required=False)
        spec.input("parent_nscf_folder", valid_type=RemoteData, required=False)
        spec.input("parameters_p2y", valid_type=ParameterData, required=False, default=set_default_qp_param()  )
        spec.input("parameters", valid_type=ParameterData, required=False  )
        #spec.input("converge_parameters", valid_type=List)
        #spec.input("starting_points", valid_type=List,required=False,default=List() )
        #spec.input("default_step_size", valid_type=ParameterData,required=False,
        #                   default=DataFactory('parameter')(dict=default_step_size))
        spec.input("convergence_parameters", valid_type=ParameterData, required=True)
        #spec.input("threshold", valid_type=Float, required=False, default=Float(0.1))

        spec.outline(
          cls.start,
          cls.iterate,
          while_(cls.is_not_converged)(
              cls.run_next_update,
              cls.iterate,
              ),
          cls.report_wf
        )
        spec.dynamic_output()



    def init_parameters(self,paging):
        convergence_parameters_dict = self.inputs.convergence_parameters.get_dict()
        if 'calculation_set_pw' not in self.inputs.keys():
            self.inputs.calculation_set_pw = DataFactory('parameter')(dict=self.inputs.calculation_set.get_dict())

        if 'calculation_set_p2y' not in self.inputs.keys():
            main_set = self.inputs.calculation_set.get_dict()
            main_set['resources'] = {"num_machines": 1,"num_mpiprocs_per_machine":  1}
            self.ctx.calculation_set_p2y = DataFactory('parameter')(dict=main_set)
        else:
            self.ctx.calculation_set_p2y =  self.inputs.calculation_set_p2y 

        if 'parameters' not in self.inputs.keys():
            self.ctx.parameters = set_default_qp_param()
        else:
            self.ctx.parameters = self.inputs.parameters

        if 'parent_scf_folder' in  self.inputs.keys(): 
            self.report("parent_scf folder was set")
            parent_calc = self.inputs.parent_scf_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
            if isinstance(parent_calc, PwCalculation):
                if parent_calc.get_state()== 'FINISHED': 
                    if 'settings_pw' not in self.inputs.keys():
                        self.ctx.settings_pw = parent_calc.inp.settings
                    if 'structure' not in self.inputs.keys():
                        self.inputs.structure = parent_calc.inp.structure
                    if 'pseudo' not in self.inputs.keys():
                        raise InputValidationError("Pseudo should be provided")
                    if parent_calc.get_inputs_dict(link_type=LinkType.CREATE)['parameters'].get_dict()['CONTROL']['calculation'] == 'scf':
                        if 'parameters_pw' not in self.inputs.keys():
                            self.ctx.parameters_pw = parent_calc.inp.parameters
                    else:
                        if 'parameters_pw_nscf' not in self.inputs.keys():
                            self.ctx.parameters_pw_nscf = parent_calc.inp.parameters
                    self.report("parent_scf_folder defined params {}".format(self.ctx.parameters.get_dict() ))

            if isinstance(parent_calc, YamboCalculation):
                if parent_calc.get_state()== 'FINISHED': 
                    if 'parameters' not in self.inputs.keys():
                        self.report("setting default parameters, parent was yambocalc ")
                        self.ctx.parameters = set_default_qp_param()

            if 'kpoints'==self.ctx.variable_to_converge:
                if 'settings_pw' not in self.inputs.keys():
                    self.ctx.settings_pw =  default_pw_settings() 
                if 'parameters_pw' not in self.inputs.keys():
                    self.ctx.parameters_pw = set_default_pw_param() 
                if 'parameters_pw_nscf' not in self.inputs.keys():
                    self.ctx.parameters_pw_nscf = set_default_pw_param(nscf=True) 
                      
        else:
            if 'kpoints'==self.ctx.variable_to_converge:
                self.report(" initializing in a kpoints convergence calculation")
                if 'settings_pw' not in self.inputs.keys():
                    self.ctx.settings_pw =  default_pw_settings() 
                if 'parameters_pw' not in self.inputs.keys():
                    self.report("  parameters_pw were not found setting them to default pw params")
                    self.ctx.parameters_pw = set_default_pw_param() 
                if 'parameters_pw_nscf' not in self.inputs.keys():
                    self.report("  parameters_pw_nscf were not found setting them to default pw params")
                    self.ctx.parameters_pw_nscf = set_default_pw_param(nscf=True) 
            if 'kpoints'!=self.ctx.variable_to_converge:
                if 'settings_pw' not in self.inputs.keys():
                    self.ctx.settings_pw =  default_pw_settings() 
                if 'parameters' not in self.inputs.keys():
                    self.ctx.parameters = set_default_qp_param()
            if 'structure' not in self.inputs.keys() :
                raise InputValidationError("Structure should be provided if parent PW SCF folder is not given when converging kpoints")
            if 'pseudo' not in self.inputs.keys():
                raise InputValidationError("Pseudo should be provided if parent PW calculation is not given when converging kpoints")
            if 'pwcode' not in self.inputs.keys():
                raise InputValidationError("PW code  should be provided when converging kpoints")
            if 'kpoints'!=self.ctx.variable_to_converge and\
                                                   'parent_nscf_folder' not in self.inputs.keys():
                raise InputValidationError("Parent nscf folder should be provided when not converging kpoints")

        if 'parent_nscf_folder' in  self.inputs.keys():
              parent_calc = load_node(self.inputs.parent_nscf_folder.get_inputs_dict()['remote_folder'].pk)
              if isinstance(parent_calc, PwCalculation):
                  if parent_calc.get_inputs_dict()['parameters'].get_dict()['CONTROL']['calculation'] == 'nscf'\
                                      and parent_calc.get_state()== 'FINISHED'\
                                      and 'QPkrange' not in self.ctx.parameters.get_dict().keys():
                      self.ctx.parameters = default_qpkrange(parent_calc.pk, self.ctx.parameters)
                      self.report("QPkrange not in  self.ctx.parameters.get_dict keys ")

        if 'settings_pw' in self.inputs.keys():
            self.ctx.settings_pw =  self.inputs.settings_pw 

        params = self.ctx.parameters.get_dict() 
        if 'kpoints'!=self.ctx.variable_to_converge:
            for field in self.ctx.conv_elem.keys():
                 self.report("self.ctx.start_value {}  self.ctx.step {}  self.ctx.loop_length {}  self.ctx.iteration {}".format(
                             self.ctx.start_value, self.ctx.step, self.ctx.loop_length, self.ctx.iteration ))
                 starting_point = self.ctx.start_value +\
                                  self.ctx.step * self.ctx.loop_length * self.ctx.iteration  
                 params[ field ] = update_parameter_field( field, starting_point, self.ctx.step*paging)
                 self.ctx.conv_elem[field].append(params[field])
            self.ctx.parameters = DataFactory('parameter')(dict= params)
        self.report('Initialization step completed.' )

    def start(self):
        # for kpoints, we will need to have the scf step, and  use YamboWorkflow not YamboRestartWf
        #
        self.ctx.max_iterations = 20 
        self.ctx.iteration = 0
        self.ctx.skip_prescf = False
        self.ctx.very_first = True
        convergence_parameters_dict = self.inputs.convergence_parameters.get_dict()
        # Mandatory inputs
        try:
            self.ctx.variable_to_converge = convergence_parameters_dict['variable_to_converge']
        except KeyError:
            raise InputValidationError('variable_to_converge not defined in input!')
        try:
            self.ctx.start_value = convergence_parameters_dict['start_value']
        except KeyError:
            raise InputValidationError('start_value not defined in input!')  
        try:
            self.ctx.step = convergence_parameters_dict['step']
        except KeyError:
            raise InputValidationError('step not defined in input!')  
        try:
            self.ctx.max_value = convergence_parameters_dict['max_value']
        except KeyError:            
            raise InputValidationError('max_value not defined in input!') 
        try:                        
            self.ctx.conv_tol = convergence_parameters_dict['conv_tol']
        except KeyError:
            raise InputValidationError('conv_tol not defined in input!')  
        # Optional inputs          
        try:
            self.ctx.conv_window = convergence_parameters_dict['conv_window']
        except KeyError:
            self.ctx.conv_window = 3
        try:
            self.ctx.loop_length = convergence_parameters_dict['loop_length']
        except KeyError:
            self.ctx.loop_length = 4
        self.ctx.distance_kpoints = self.ctx.start_value 
        self.ctx.en_diffs = []
        if self.ctx.variable_to_converge=='bands':
            self.ctx.conv_elem = {'BndsRnXp':[],'GbndRnge': []}
        elif self.ctx.variable_to_converge=='W_cutoff':
            self.ctx.conv_elem = {'NGsBlkXp':[]}
        elif self.ctx.variable_to_converge=='FFT_cutoff':
            self.ctx.conv_elem = {'FFTGvecs':[]}
        elif self.ctx.variable_to_converge=='kpoints':
            self.ctx.conv_elem = {'kpoints':[]}
        else:
            self.ctx.conv_elem = {self.ctx.variable_to_converge:[]}
            self.report('WARNING: the variable to converge is {}, not recognized but I try anyway to converge it') 
        self.report("Setup step completed.")

    def run_next_update(self):
        if self.ctx.skip_prescf: 
            p2y_parent = load_node( self.ctx.missing_p2y_parent.out.gw.get_dict()["yambo_pk"])
            self.ctx.p2y_parent_folder = p2y_parent.out.remote_folder
            self.ctx.skip_prescf = False

    def iterate(self):
        self.report("Convergence iteration {}".format(str(self.ctx.iteration)))
        loop_items = range(1,self.ctx.loop_length+1)
        if self.ctx.very_first == True:
            loop_items = range(self.ctx.loop_length)
            self.ctx.very_first = False
        self.report('will run four calculations in parallel' )
        outs={}
        if 'kpoints'!=self.ctx.variable_to_converge:
            self.report("this is not a K-point convergence ")
            for num in loop_items: # includes 0 because of starting point
                # There is a bug here, for Bands we might end up 
                # with a situation like BandsRnXP  %   12 | 12  % where both
                # are equal at the very start, this is due to the fact that we need
                # to be able to support BSE calculations too.
                # TODO
                if loop_items[0] == 0:
                    if  'bands' == self.ctx.variable_to_converge:
                        self.init_parameters(num+1) # see above comment
                    else:
                        self.init_parameters(num)
                else:
                    if  'bands' == self.ctx.variable_to_converge:
                        self.update_parameters(num+1)
                    else:
                        self.update_parameters(num)
                try: 
                    p2y_done = self.ctx.p2y_parent_folder 
                except AttributeError:
                    self.report(' no preceeding yambo parent, will run P2Y from NSCF parent first ' )
                    p2y_res =  submit (YamboRestartWf,
                                precode= self.inputs.precode,
                                yambocode=self.inputs.yambocode,
                                parameters = self.inputs.parameters_p2y,
                                calculation_set= self.ctx.calculation_set_p2y,
                                parent_folder = self.inputs.parent_nscf_folder, settings = self.inputs.settings_p2y) 
                    self.ctx.skip_prescf = True
                    #self.ctx.iteration-=1  
                    self.ctx.very_first = True
                    return ToContext(missing_p2y_parent= p2y_res)
                self.report(' running from preceeding yambo/p2y calculation  ' )
                future =  submit  (YamboRestartWf,
                            precode= self.inputs.precode,
                            yambocode=self.inputs.yambocode,
                            parameters = self.ctx.parameters,
                            calculation_set= self.inputs.calculation_set,
                            parent_folder = self.ctx.p2y_parent_folder, settings = self.inputs.settings)
                outs[ 'r'+str(num) ] =  future
            self.ctx.iteration = self.ctx.iteration + 1
            return ToContext(**outs )
        else:
            # run yambowf, four times. with a different  nscf kpoint starting mesh
            self.report("  K-point convergence commencing")
            for num in loop_items: # includes 0 because of starting point
                if loop_items[0] == 0:
                    self.init_parameters(num)
                #else: 
                #    self.update_parameters(num)  # Not neccessary, kpoint variation is done at PBE level with the self.ctx.distance_kpoints

                self.ctx.distance_kpoints = self.ctx.distance_kpoints* 0.80 # 15% change 
                kpoints = KpointsData()
                kpoints.set_cell_from_structure(self.inputs.structure)
                kpoints.set_kpoints_mesh_from_density(distance= self.ctx.distance_kpoints,force_parity=False)
                extra = {}
                if 'parent_scf_folder' in self.inputs.keys():
                   extra['parent_folder'] = self.inputs.parent_scf_folder
                if 'QPkrange' not in self.ctx.parameters.get_dict().keys():
                   extra['to_set_qpkrange'] = Bool(1)
                extra['calculation_set_p2y'] = self.ctx.calculation_set_p2y
                extra['calculation_set_pw'] = self.inputs.calculation_set_pw
                extra['settings_p2y'] = self.inputs.settings_p2y
                extra['settings_pw'] = self.ctx.settings_pw
                future =  submit (YamboWorkflow, codename_pw= self.inputs.pwcode, codename_p2y=self.inputs.precode,
                   codename_yambo= self.inputs.yambocode, pseudo_family= self.inputs.pseudo,
                   calculation_set_yambo = self.inputs.calculation_set,
                   settings_yambo=self.inputs.settings , structure = self.inputs.structure,
                   kpoint_pw = kpoints, parameters_pw= self.ctx.parameters_pw, parameters_pw_nscf= self.ctx.parameters_pw_nscf,
                   parameters_p2y= self.inputs.parameters_p2y, parameters_yambo=  self.ctx.parameters,
                   **extra)
                outs[ 'r'+str(num) ] = future
            self.ctx.conv_elem['kpoints'].append(self.ctx.distance_kpoints)
            self.ctx.iteration = self.ctx.iteration + 1
            return ToContext(**outs )  
        return outs 


    def update_parameters(self, paging):
        params = self.ctx.parameters.get_dict()
        for field in self.ctx.conv_elem.keys():
             starting_point = self.ctx.start_value +\
                              self.ctx.step * self.ctx.loop_length* self.ctx.iteration
             if starting_point <0 :
                 self.report("*** ERROR:  updating in the negative direction, please check: starting_point {}".format(starting_point))
                 self.report("*** ERROR:  self.ctx.start_value  {}".format(self.ctx.start_value))
                 self.report("*** ERROR:  self.ctx.step  {}".format(self.ctx.step))
                 self.report("*** ERROR:  self.ctx.loop_length  {}".format(self.ctx.loop_length))
                 self.report("*** ERROR:  self.ctx.iteration  {}".format(self.ctx.iteration))
             params[ field ] = update_parameter_field( field, starting_point, self.ctx.step*paging)
             self.ctx.conv_elem[field].append(params[field])
        self.report(" extended convergence points: {}".format(self.ctx.conv_elem))
        self.ctx.parameters = DataFactory('parameter')(dict= params)


    def is_not_converged(self):
        if self.ctx.skip_prescf == True:
            return True 
        try: # for yamborestart
            r0_width = self.get_total_range(self.ctx.r0.out.gw.get_dict()['yambo_pk'])
            r1_width = self.get_total_range(self.ctx.r1.out.gw.get_dict()['yambo_pk'])
            r2_width = self.get_total_range(self.ctx.r2.out.gw.get_dict()['yambo_pk'])
            r3_width = self.get_total_range(self.ctx.r3.out.gw.get_dict()['yambo_pk'])
        except AttributeError: # for yamboworkflow
            r0_width = self.get_total_range(self.ctx.r1.out.gw.get_dict()['yambo_pk'])
            r1_width = self.get_total_range(self.ctx.r2.out.gw.get_dict()['yambo_pk'])
            r2_width = self.get_total_range(self.ctx.r3.out.gw.get_dict()['yambo_pk'])
            r3_width = self.get_total_range(self.ctx.r4.out.gw.get_dict()['yambo_pk'])

        self.ctx.en_diffs.extend([r0_width,r1_width,r2_width,r3_width])
        if 'scf_pk' in self.ctx.r1.out.gw.get_dict() and 'parent_scf_folder' not in self.inputs.keys():
            self.inputs.parent_scf_folder =  load_node(self.ctx.r1.out.gw.get_dict()['scf_pk']).out.remote_folder
        if len(self.ctx.en_diffs) > self.ctx.max_iterations: # no more than 16 calcs
            self.report("Aborting after max_iterations={} calculations with no convergence ".format(self.ctx.max_iterations))
            return False
        if 'kpoints' ==self.ctx.variable_to_converge:
            if self.ctx.distance_kpoints <= self.ctx.max_value:
                self.report("Aborting, k-point  convergence not achived within given mesh density range {}- {}".format(0.5,self.ctx.max_value))
                return False
          
        field = self.ctx.conv_elem.keys()[0]
        independent = np.array(self.ctx.conv_elem[field])
        dependent = np.array(self.ctx.en_diffs)
        values = dependent[-4:]
        is_conv =  is_converged(values,conv_tol=self.ctx.conv_tol,conv_window=self.ctx.conv_window)
        if is_conv:
            converged_fit = self.analyse_fit(field)
            if converged_fit:
               self.report("Fit convergence achieved. ")
            else:
               self.report("Fit convergence not achieved.")
            return False
        self.report(" k-point convergence has not been achieved, continuing iterations")
        return True

    def analyse_fit(self,field):
        """
        Docs

        independent means the input values
        dependent the quantity to converge (e.g. band gap)
        """
        independent = np.array(self.ctx.conv_elem[field])
        if self.ctx.variable_to_converge== 'bands':
            if len(independent.shape) >1:
                independent = independent[:,1]
        dependent = np.array(self.ctx.en_diffs)
        self.report("indep and dependent  {}  {} ".format(independent, dependent))
        def func(x,a,b):
            y = 1.0
            y = y*(a/x+b)
            return y
        popt,pcov = curve_fit(func,independent[-4:],dependent[-4:])
        a,b = popt
        fit_data = func(independent, a,b)      
        deviations = np.abs(dependent[-4:] - fit_data[-4:])  # deviation of last four from extrapolated values at those points
        converged_fit = np.allclose(deviations, np.linspace(0.01,0.01, 4), atol=self.ctx.conv_tol) # last four are within 0.01 of predicted value
        self.report("Fitting_deviation: converged_fit {}".format(converged_fit))
        return converged_fit
 

    def get_total_range(self,node_id):
        # CAVEAT: this does not calculate HOMO LUMO gap, but the width between two
        #         bands listed in the QPkrange, on the first kpoint selected,
        #         i.e. for 'QPkrange': [(1,16,30,31)] , will find width between 
        #         kpoint 1  band 30 and kpoint  1 band 31. 
        calc = load_node(node_id)
        table=calc.out.array_qp.get_array('qp_table')
        try:
            qprange = calc.inp.parameters.get_dict()['QPkrange']
        except KeyError: 
            parent_calc =  calc.inp.parent_calc_folder.inp.remote_folder
            if isinstance(parent_calc, YamboCalculation):
                has_found_nelec = False
                while (not has_found_nelec):
                    try:
                        nelec = parent_calc.out.output_parameters.get_dict()['number_of_electrons']
                        has_found_nelec = True
                    except AttributeError:
                        parent_calc = parent_calc.inp.parent_calc_folder.inp.remote_folder
                    except KeyError:
                        parent_calc = parent_calc.inp.parent_calc_folder.inp.remote_folder
            elif isinstance(parent_calc, PwCalculation):
                nelec  = parent_calc.out.output_parameters.get_dict()['number_of_electrons']
            qprange =  [ ( 1, 1 , int(nelec/2) , int(nelec/2)+1 ) ]
        lowest_k = qprange[0][0] # first kpoint listed, 
        lowest_b = qprange[0][-2] # first band on first kpoint listed,
        highest_b= qprange[0][-1]  # last band on first kpoint listed,
        argwlk = np.argwhere(table[:,0]==float(lowest_k))  # indexes for lowest kpoint
        argwlb = np.argwhere(table[:,1]==float(lowest_b))  # indexes for lowest band
        argwhb = np.argwhere(table[:,1]==float(highest_b)) # indexes for highest band
        if len(argwlk)< 1:
            argwlk = np.array([0])
        if len(argwhb) < 1:
            argwhb = np.argwhere(table[:,1]== table[:,1][np.argmax(table[:,1])])
            argwlb = np.argwhere(table[:,1]== table[:,1][np.argmax(table[:,1])]-1 )
        arglb = np.intersect1d(argwlk,argwlb)              # index for lowest kpoints' lowest band
        arghb = np.intersect1d(argwlk,argwhb)              # index for lowest kpoint's highest band
        e_m_eo = calc.out.array_qp.get_array('E_minus_Eo') 
        eo = calc.out.array_qp.get_array('Eo')
        corrected = eo+e_m_eo
        corrected_lb = corrected[arglb]
        corrected_hb = corrected[arghb]
        self.report(" corrected gap(s)   at K-point {}, between bands {} and {}".format(
                    corrected_hb- corrected_lb, lowest_k, lowest_b, highest_b ))
        return (corrected_hb- corrected_lb)[0]  # for spin polarized there will be two almost equivalent, else just one value.

    def report_wf(self):
        """
        Output final quantities
        """
        extra = {}
        nscf_pk = False
        scf_pk = False
        parameters = None
        from aiida.orm import DataFactory
        if 'nscf_pk' in self.ctx.r1.out.gw.get_dict():
            nscf_pk = self.ctx.r1.out.gw.get_dict()['nscf_pk'] 
            self.out("nscf_remote_folder", self.ctx.r1.out.nscf_remote_folder)
        if 'scf_pk' in self.ctx.r1.out.gw.get_dict():
            scf_pk = self.ctx.r1.out.gw.get_dict()['scf_pk'] 
            self.out("scf_remote_folder", self.ctx.r1.out.scf_remote_folder)
        if 'yambo_pk' in self.ctx.r1.out.gw.get_dict():
            parameters = load_node( self.ctx.r1.out.gw.get_dict()['yambo_pk']).inp.parameters.get_dict()
            self.out("yambo_remote_folder", self.ctx.r1.out.yambo_remote_folder)
        self.out("convergence", DataFactory('parameter')(dict={
            "parameters": parameters,
            "yambo_pk": self.ctx.r1.out.gw.get_dict()['yambo_pk'],
            "convergence_space": self.ctx.conv_elem,
            "energy_widths":  self.ctx.en_diffs ,
            "nscf_pk":  nscf_pk, 
            "scf_pk":  scf_pk , 
            }))
        self.report("completed 1-D convergence workflow")

if __name__ == "__main__":
    pass
