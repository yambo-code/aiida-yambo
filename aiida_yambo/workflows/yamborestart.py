import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.common.exceptions import InputValidationError,ValidationError
from aiida.orm.data.upf import get_pseudos_from_structure
from aiida.common.datastructures import calc_states
from collections import defaultdict
from aiida.orm.utils import DataFactory, CalculationFactory
from aiida.orm.data.base import Float, Str, NumericType, BaseType 
from aiida.work.workchain import WorkChain, while_ , Outputs
from aiida.work.workchain import ToContext as ResultToContext
from aiida.work.run import legacy_workflow
from aiida.work.run import run, submit
from aiida.common.links import LinkType
from aiida.orm.data.remote import RemoteData 
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida_yambo.calculations.gw  import YamboCalculation
from aiida_yambo.workflows.yambo_utils import generate_yambo_input_params, reduce_parallelism 
from aiida_quantumespresso.calculations.pw import PwCalculation

#PwCalculation = CalculationFactory('quantumespresso.pw')
#YamboCalculation = CalculationFactory('yambo.yambo')

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")

"""
"""
class YamboRestartWf(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        """
        Workfunction definition
        """
        super(YamboRestartWf, cls).define(spec)
        spec.input("precode", valid_type=Str)
        spec.input("yambocode", valid_type=Str)
        spec.input("calculation_set", valid_type=ParameterData)
        spec.input("settings", valid_type=ParameterData)
        spec.input("parent_folder", valid_type=RemoteData)
        spec.input("parameters", valid_type=ParameterData)
        spec.input("restart_options", valid_type=ParameterData, required=False)
        spec.outline(
            cls.yambobegin,
            while_(cls.yambo_should_restart)(
                cls.yambo_restart,
                cls.interstep,
            ),
            cls.report_wf
        )
        spec.dynamic_output()

    def yambobegin(self):
        """
        Run the  pw-> yambo conversion, init and yambo run
        #  precodename,yambocodename, parent_folder, parameters,  calculation_set=None, settings
        """
        self.ctx.yambo_pks = []
        self.ctx.yambo_nodes = []
        self.ctx.restart = 0 
        # run YamboCalculation
        if not isinstance(self.inputs.parent_folder, RemoteData):
            raise InputValidationError("parent_calc_folder must be of"
                                       " type RemoteData")        
        self.ctx.last = ''
        self.ctx.parameters = self.inputs.parameters
        self.ctx.calculation_set = self.inputs.calculation_set
        new_settings = self.inputs.settings.get_dict()
        parent_calc = self.inputs.parent_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
        yambo_parent = isinstance(parent_calc, YamboCalculation)
        if 'INITIALISE' not in new_settings.keys() and not yambo_parent:
            new_settings['INITIALISE'] = True
            self.ctx.last = 'INITIALISE'
        try:
            restart_options = self.inputs.restart_options
            try:
                max_restarts = restart_options.get_dict()['max_restarts']
            except KeyError:
                max_restarts = 5
        except AttributeError:
            restart_options = None
            max_restarts = 5
        self.ctx.max_restarts = max_restarts
        inputs = generate_yambo_input_params(
            self.inputs.precode,self.inputs.yambocode,
            self.inputs.parent_folder, self.ctx.parameters, self.ctx.calculation_set, ParameterData(dict=new_settings) )
        future = self.run_yambo(inputs)
        self.report("workflow start, submitted  {}".format(future.pid))
        return  ResultToContext(yambo= future)

    def interstep(self):
        # convenience function that stores output of resolved future  before the next loop if any, 
        # of no loop will run, it is still useful for the report_wf to find the resolved future's node
        # in the context. 
        self.ctx.yambo_nodes.append(self.ctx.yambo)

    def yambo_should_restart(self):
        """
        # should restart a calculation if it satisfies either
        # 1. It has not been restarted  X times already.
        # 2. It hasnt produced output.
        # 3. Submission failed.
        # 4. Failed: a) Memory problems
        #            b) Parallelism problems.
        #            c) Some input inconsistency problems (too low bands)
        """
        self.report("Checking if yambo restart is needed")
        if self.ctx.restart >= self.ctx.max_restarts:
            self.report("I will not restart: maximum restarts reached: {}".format(self.ctx.max_restarts))
            return False

        self.report("I can restart (# {}), max restarts ({}) not reached yet".format(self.ctx.restart, self.ctx.max_restarts))
        calc = load_node(self.ctx.yambo_pks[-1])
        if self.ctx.last == 'INITIALISE':
            return True

        if calc.get_state() == calc_states.SUBMISSIONFAILED:
            self.report("I will not resubmit calc pk: {}, submission failed: {}, check the log or you settings ".format(calc.pk ,calc.get_state() ))
            return False

        max_input_seconds = self.ctx.calculation_set.get_dict()['max_wallclock_seconds']

        last_time = 30 # seconds default value:
        try:
            last_time = calc.get_outputs_dict()['output_parameters'].get_dict()['last_time']  
        except Exception:
            pass  # Likely no logs were produced 
 
        if calc.get_state() == calc_states.FAILED and (float(max_input_seconds)-float(last_time))/float(max_input_seconds)*100.0 < 1:   
            max_input_seconds = int( max_input_seconds * 1.3) # 30% increase
            calculation_set = self.ctx.calculation_set.get_dict() 
            calculation_set['max_wallclock_seconds'] = max_input_seconds
            self.ctx.calculation_set = DataFactory('parameter')(dict=calculation_set) 
            self.report("Failed calculation, likely queue time exhaustion, restarting with new max_input_seconds = {}".format(
                        max_input_seconds ))
            return True

        if calc.get_state() != calc_states.PARSINGFAILED and calc.get_state != calc_states.FINISHED : # special case for parallelization needed
            output_p = {}
            if 'output_parameters'  in  calc.get_outputs_dict(): # calc.get_outputs_dict()['output_parameters'].get_dict().keys() 
                output_p = calc.get_outputs_dict()['output_parameters'].get_dict()
            if 'para_error' in output_p.keys(): 
                if output_p['para_error'] == True:  # Change parallelism or add missing parallelism inputs
                    self.report(" parallelism error detected")
                    params = self.ctx.parameters.get_dict() 
                    X_all_q_CPU = params.pop('X_all_q_CPU','')
                    X_all_q_ROLEs =  params.pop('X_all_q_ROLEs','') 
                    SE_CPU = params.pop('SE_CPU','')
                    SE_ROLEs = params.pop('SE_ROLEs','')
                    calculation_set = self.ctx.calculation_set.get_dict()
                    params['X_all_q_CPU'],calculation_set =   reduce_parallelism('X_all_q_CPU', X_all_q_ROLEs,  X_all_q_CPU, calculation_set )
                    params['SE_CPU'], calculation_set=  reduce_parallelism('SE_CPU', SE_ROLEs,  SE_CPU,  calculation_set )
                    params["X_all_q_ROLEs"] = X_all_q_ROLEs
                    params["SE_ROLEs"]= SE_ROLEs
                    self.ctx.calculation_set = DataFactory('parameter')(dict=calculation_set)
                    self.ctx.parameters = DataFactory('parameter')(dict=params)
                    self.report("Calculation {} failed from a parallelism problem: {}".format(calc.pk,output_p['errors']) )
                    self.report("Old parallelism {}= {} , {} = {} ".format(
                                    X_all_q_ROLEs,X_all_q_CPU, SE_ROLEs, SE_CPU))
                    self.report("New parallelism {}={} , {} = {}".format(
                                    X_all_q_ROLEs, params['X_all_q_CPU'], SE_ROLEs,  params['SE_CPU'] ))
                    return True 
            if 'unphysical_input' in output_p.keys():
                if output_p['unphysical_input'] == True:
                    # this handles this type of error: "[ERROR][NetCDF] NetCDF: NC_UNLIMITED in the wrong index"
                    # we should reset the bands to a larger value, it may be too small. 
                    # this is a probable cause, and it may not be the real problem, but often is the cause.
                    self.report("the calculation failed due to a problematic input, defaulting to increasing bands")
                    params = self.ctx.parameters.get_dict()
                    bandX = params.pop('BndsRnXp', None)
                    bandG = params.pop('GbndRnge', None)
                    if bandX:
                        bandX = ( bandX[0], int(bandX[0]*1.5)) # 
                        params['BndsRnXp'] = bandX
                    if bandG:
                        bandG = ( bandG[0], int(bandG[0]*1.5)) # 
                        params['GbndRnge'] = bandG
                    self.ctx.parameters = DataFactory('parameter')(dict=params)
                    return True 
                   
            if 'errors' in output_p.keys() and calc.get_state() == calc_states.FAILED:
                if len(calc.get_outputs_dict()['output_parameters'].get_dict()['errors']) < 1:
                    # No errors, We  check for memory issues, indirectly
                    if 'last_memory_time' in calc.get_outputs_dict()['output_parameters'].get_dict().keys():
                        # check if the last alloc happened close to the end:
                        last_mem_time = calc.get_outputs_dict()['output_parameters'].get_dict()['last_memory_time']
                        if  abs(last_time - last_mem_time) < 3: # 3 seconds  selected arbitrarily,
                            # this is (based on a simple heuristic guess, a memory related problem)
                            # change the parallelization to account for this before continuing, warn user too.
                            params = self.ctx.parameters.get_dict() 
                            X_all_q_CPU = params.pop('X_all_q_CPU','')
                            X_all_q_ROLEs =  params.pop('X_all_q_ROLEs','') 
                            SE_CPU = params.pop('SE_CPU','')
                            SE_ROLEs = params.pop('SE_ROLEs','')
                            calculation_set = self.ctx.calculation_set.get_dict()
                            params['X_all_q_CPU'],calculation_set =   reduce_parallelism('X_all_q_CPU', X_all_q_ROLEs,  X_all_q_CPU, calculation_set )
                            params['SE_CPU'], calculation_set=  reduce_parallelism('SE_CPU', SE_ROLEs,  SE_CPU,  calculation_set )
                            params["X_all_q_ROLEs"] = X_all_q_ROLEs
                            params["SE_ROLEs"]= SE_ROLEs
                            self.ctx.calculation_set = DataFactory('parameter')(dict=calculation_set)
                            self.ctx.parameters = DataFactory('parameter')(dict=params)
                            self.report("Calculation  {} failed likely from memory issues")
                            self.report("Old parallelism {}= {} , {} = {} ".format(
                                                  X_all_q_ROLEs,X_all_q_CPU, SE_ROLEs, SE_CPU))
                            self.report("New parallelism selected {}={}, {} = {} ".format(
                                                  X_all_q_ROLEs, params['X_all_q_CPU'], SE_ROLEs,  params['SE_CPU'] ))
                            return True 
                        else:
                            pass
            
        if calc.get_state() == calc_states.SUBMISSIONFAILED\
                   or calc.get_state() == calc_states.FAILED\
                   or 'output_parameters' not in calc.get_outputs_dict():
            self.report("Calculation {} failed or did not genrerate outputs for unknow reason, restarting with no changes".format(calc.pk))
            return True
        return False

    def yambo_restart(self):
        """
        restart if necessary
        get inputs from prior calculation ctx.yambo_pks
        should be able to handle submission failed, by possibly going to parent?
        """

        calc = load_node(self.ctx.yambo_pks[-1])
        if  calc.get_state() == calc_states.SUBMISSIONFAILED:
            calc = self.get_last_submitted(calc.pk)
            if not calc: 
                raise ValidationError("restart calculations can not start from"
                                       "calculations in SUBMISSIONFAILED state")
                return        
        #parameters = calc.get_inputs_dict()['parameters'].get_dict()
        
        parent_folder = calc.out.remote_folder
        new_settings = self.inputs.settings.get_dict()

        parent_calc = parent_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
        yambo_parent = isinstance(parent_calc, YamboCalculation)
        p2y_restart =  calc.get_state() != calc_states.FINISHED and calc.inp.settings.get_dict().pop('INITIALISE',None)==True 
            
        if not yambo_parent or p2y_restart == True: 
            new_settings['INITIALISE'] =  True
            self.ctx.last = 'INITIALISE'
            self.report(" restarting from: {}, a P2Y calculation ".format(self.ctx.yambo_pks[-1]))
        else:
            new_settings['INITIALISE'] =  False
            self.ctx.last = 'NOTINITIALISE'
            self.report(" restarting from: {},  a GW calculation ".format(self.ctx.yambo_pks[-1]))
        inputs = generate_yambo_input_params(
             self.inputs.precode,self.inputs.yambocode,
             parent_folder, self.ctx.parameters, self.ctx.calculation_set, ParameterData(dict=new_settings) )
        future = self.run_yambo(inputs)
        self.ctx.yambo_pks.append(future.pid )
        self.ctx.restart += 1
        self.report(" restarting from:{}  ".format(future.pid )) 
        return ResultToContext(yambo_restart= future)

    def run_yambo(self,inputs):
        YamboProcess = YamboCalculation.process()
        future =  submit(YamboProcess, **inputs)
        self.ctx.yambo_pks.append( future.pid )
        self.report(" submitted a calculation with pk: {} ".format(future.pid ))
        return future  # we can not  ReturnToContext since this fuction is not called from the outline 


    def get_last_submitted(self, pk):
        submited = False
        depth = 0
        while not submited and depth <4:
            calc = load_node(pk)
            if  calc.get_state() == calc_states.SUBMISSIONFAILED:
                pk = load_node(calc.inp.parent_calc_folder.inp.remote_folder.pk).pk
            else:
                submited = calc
            depth+=1
        return  submited

    def report_wf(self):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        from aiida.orm import DataFactory
        success = load_node(self.ctx.yambo_pks[-1]).get_state()== 'FINISHED' 
        self.out("gw", DataFactory('parameter')(dict={ "yambo_pk":   self.ctx.yambo_pks[-1],  "success": success }))
        self.out("yambo_remote_folder",  load_node(self.ctx.yambo_pks[-1]).out.remote_folder )
        self.report("workflow completed ")

if __name__ == "__main__":
    pass
