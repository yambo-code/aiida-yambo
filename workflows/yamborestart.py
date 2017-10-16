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

from aiida.orm.data.remote import RemoteData 
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.workflows.user.cnr_nano.yambo_utils import generate_yambo_input_params, reduce_parallelism 
from aiida_quantumespresso.calculations.pw import PwCalculation

#PwCalculation = CalculationFactory('quantumespresso.pw')
YamboCalculation = CalculationFactory('yambo.yambo')

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
YamboProcess = YamboCalculation.process()

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
        spec.outline(
            cls.yambobegin,
            while_(cls.yambo_should_restart)(
                cls.yambo_restart,
            ),
            cls.report
        )
        spec.dynamic_output()

    def yambobegin(self):
        """
        Run the  pw-> yambo conversion, init and yambo run
        #  precodename,yambocodename, parent_folder, parameters,  calculation_set=None, settings
        """
        # run YamboCalculation
        if not isinstance(self.inputs.parent_folder, RemoteData):
            raise InputValidationError("parent_calc_folder must be of"
                                       " type RemoteData")        
        parameters = self.inputs.parameters
        print("yamborestart: yambobegin() ")
        inputs = generate_yambo_input_params(
             self.inputs.precode.copy(),self.inputs.yambocode.copy(),
             self.inputs.parent_folder, parameters, self.inputs.calculation_set.copy(), self.inputs.settings.copy() )
        future =  submit(YamboProcess, **inputs)
        self.ctx.yambo_pks = []
        self.ctx.yambo_pks.append(future.pid)
        self.ctx.restart = 0 
        return  ResultToContext(yambo= Outputs(future))

    def yambo_should_restart(self):
        # should restart a calculation if it satisfies either
        # 1. It hasnt been restarted  X times already.
        # 2. It hasnt produced output.
        # 3. Submission failed.
        # 4. Failed: a) Memory problems
        #            b) 
        print("yamborestart: yambo_should_restart() ")
        if self.ctx.restart >= 5:
            return False

        calc = load_node(self.ctx.yambo_pks[-1])
        if calc.get_state() == calc_states.SUBMISSIONFAILED:
                   #or calc.get_state() == calc_states.FAILED\
                   #or 'output_parameters' not in calc.get_outputs_dict():
            return False

        max_input_seconds = self.inputs.calculation_set.get_dict()['max_wallclock_seconds']

        last_time = 30 # seconds default value:
        try:
            last_time = calc.get_outputs_dict()['output_parameters'].get_dict()['last_time']  
        except Exception:
            pass  # Likely no logs were produced 
 
        if calc.get_state() == calc_states.FAILED and (float(max_input_seconds)-float(last_time))/float(max_input_seconds)*100.0 < 1:   
            max_input_seconds = int( max_input_seconds * 1.3)
            calculation_set = self.inputs.calculation_set.get_dict() 
            calculation_set['max_wallclock_seconds'] = max_input_seconds
            self.inputs.calculation_set = DataFactory('parameter')(dict=calculation_set) 
            return True

        if calc.get_state() != calc_states.PARSINGFAILED and calc.get_state != calc_states.FINISHED : # special case for parallelization needed
            output_p = {}
            if 'output_parameters'  in  calc.get_outputs_dict(): # calc.get_outputs_dict()['output_parameters'].get_dict().keys() 
                output_p = calc.get_outputs_dict()['output_parameters'].get_dict()
            if 'para_error' in output_p.keys(): 
                print ("yamborestart: yambo_should_restart:  parallelism error  ", output_p['para_error'])
                if output_p['para_error'] == True:  # Change parallelism or add some
                    params = self.inputs.parameters.get_dict() 
                    X_all_q_CPU = params.pop('X_all_q_CPU','')
                    X_all_q_ROLEs =  params.pop('X_all_q_ROLEs','') 
                    SE_CPU = params.pop('SE_CPU','')
                    SE_ROLEs = params.pop('SE_ROLEs','')
                    calculation_set = self.inputs.calculation_set.get_dict()
                    params['X_all_q_CPU'],calculation_set =   reduce_parallelism('X_all_q_CPU', X_all_q_ROLEs,  X_all_q_CPU, calculation_set )
                    params['SE_CPU'], calculation_set=  reduce_parallelism('SE_CPU', SE_ROLEs,  SE_CPU,  calculation_set )
                    self.inputs.calculation_set = DataFactory('parameter')(dict=calculation_set)
                    self.inputs.parameters = DataFactory('parameter')(dict=params)
                    print ("returning true for para_error  ", output_p['para_error'])
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
                            params = self.inputs.parameters.get_dict() 
                            X_all_q_CPU = params.pop('X_all_q_CPU','')
                            X_all_q_ROLEs =  params.pop('X_all_q_ROLEs','') 
                            SE_CPU = params.pop('SE_CPU','')
                            SE_ROLEs = params.pop('SE_ROLEs','')
                            calculation_set = self.inputs.calculation_set.get_dict()
                            params['X_all_q_CPU'],calculation_set =   reduce_parallelism('X_all_q_CPU', X_all_q_ROLEs,  X_all_q_CPU, calculation_set )
                            params['SE_CPU'], calculation_set=  reduce_parallelism('SE_CPU', SE_ROLEs,  SE_CPU,  calculation_set )
                            self.inputs.calculation_set = DataFactory('parameter')(dict=calculation_set)
                            self.inputs.parameters = DataFactory('parameter')(dict=params)
                            return True 
                        else:
                            pass
            
        if calc.get_state() == calc_states.SUBMISSIONFAILED\
                   or calc.get_state() == calc_states.FAILED\
                   or 'output_parameters' not in calc.get_outputs_dict():
            return True
        return False

    def yambo_restart(self):
        # restart if neccessary
        # get inputs from prior calculation ctx.yambo_pks
        # should be able to handle submission failed, by possibly going to parent?
        print("yamborestart: yambo_restart():  YamboRestartWF restarting from:  ", self.ctx.yambo_pks[-1],) 
        calc = load_node(self.ctx.yambo_pks[-1])
        if  calc.get_state() == calc_states.SUBMISSIONFAILED:
            calc = self.get_last_submitted(calc.pk)
            if not calc: 
                raise ValidationError("restart calculations can not start from"
                                       "calculations in SUBMISSIONFAILED state")
                return        

        parameters = calc.get_inputs_dict()['parameters'].get_dict()
        parent_folder = calc.out.remote_folder
        inputs = generate_yambo_input_params(
             self.inputs.precode.copy(),self.inputs.yambocode.copy(),
             parent_folder, ParameterData(dict=parameters), self.inputs.calculation_set.copy(), self.inputs.settings.copy())
        future =  submit (YamboProcess, **inputs)
        self.ctx.yambo_pks.append(future.pid)
        self.ctx.restart += 1
        return ResultToContext(yambo_restart= Outputs(future))

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

    def report(self):
        """
        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        from aiida.orm import DataFactory
        success = load_node(self.ctx.yambo_pks[-1]).get_state()== 'FINISHED' 
        self.out("gw", DataFactory('parameter')(dict={ "yambo_pk":   self.ctx.yambo_pks[-1], "success": success }))

if __name__ == "__main__":
    pass
