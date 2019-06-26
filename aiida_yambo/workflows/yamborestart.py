from __future__ import absolute_import
import sys

from aiida import load_profile
load_profile()

from aiida.orm import RemoteData
from aiida.orm import Code
from aiida.orm import StructureData
from aiida.orm import Float, Str, NumericType, Dict, Int
from aiida.orm import load_node

from aiida.common import InputValidationError, ValidationError
from aiida.common.links import LinkType
from aiida.common import CalcJobState
from collections import defaultdict

from aiida.plugins import DataFactory, CalculationFactory

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import run, submit

from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.utils.pseudopotential import get_pseudos_from_structure

from aiida_yambo.calculations.gw import YamboCalculation
from aiida_yambo.workflows.yambo_utils import generate_yambo_input_params, reduce_parallelism

YamboCalculation = CalculationFactory('yambo.yambo')

class YamboRestartWf(WorkChain):
    """This module interacts directly with the yambo plugin to submit calculations

    This module submits calculations using the yambo plugin, and manages them, including
    restarting the calculation in case of:
    1. Memory problems (will reduce MPI parallelism before resubmitting)
    2. Queue time exhaustions (will increase time by a fraction before resubmitting)
    3. Parallelism errors (will reduce the MPI the parallelism before resubmitting)
    4. Errors originating from a few select unphysical input parameters like too low bands.
    """

    @classmethod
    def define(cls, spec):
        """Workflow input parameters and the spec definition

        This function has a list of inputs that this workflow accepts, as well as the
        high level workflow iteration logic

        Keyword arguments:
        precode -- the P2Y code  (required)
        yambocode -- the yambo code  (required)
        calculation_set -- scheduler settings  (required)
        settings -- code settings  (required)
        parent_folder -- parent NSCF/P2Y/YAMBO calculation  (required)
        parameters -- yambo parameter  (required)
        restart_options -- the P2Y code  (optional)
        """
        super(YamboRestartWf, cls).define(spec)
        spec.input("precode", valid_type=Str)
        spec.input("yambocode", valid_type=Str)
        spec.input("calculation_set", valid_type=Dict)
        spec.input("settings", valid_type=Dict)
        spec.input("parent_folder", valid_type=RemoteData)
        spec.input("parameters", valid_type=Dict)
        spec.input("restart_options", valid_type=Dict, required=False)

        spec.outline(
            cls.yambobegin,
            while_(cls.yambo_should_restart)(
                cls.yambo_restart),
            cls.report_wf
        )



    def yambobegin(self):
        """Submits a calculation  using the  yambo plugin.

        This function takes inputs provided and using the YamboCalculation class
        submits a calculation.
        This will run only *ONE* calculation at a time,  it may be a p2y conversion or a yambo init or  a yambo calculation run,
        P2Y conversion will be done by providing a parent calculation of type PW,
        Initialize (yambo init) calculation can be done independently by having the INITIALISE key in the settings dict.
        Yambo Calc will be done when the parent calculation is P2Y/other yambo calculation, and INITIALISE is not provided.
        """
        self.ctx.yambo_pks = []
        self.ctx.restart = 0
        # run YamboCalculation
        if not isinstance(self.inputs.parent_folder, RemoteData):
            raise InputValidationError("parent_folder must be of"
                                       " type RemoteData")
        self.ctx.parameters = self.inputs.parameters
        self.ctx.calculation_set = self.inputs.calculation_set
        new_settings = self.inputs.settings.get_dict()

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
            self.inputs.precode, self.inputs.yambocode,
            self.inputs.parent_folder, self.ctx.parameters,
            self.ctx.calculation_set, Dict(dict=new_settings))

        future = self.run_yambo(inputs)
        self.report("Workflow started, submitted process with pk = {}".format(future.pk))
        return ToContext(yambo=future)

    def yambo_should_restart(self):
        """This function encodes the logic to restart calculations from failures

        This function supports detecting failed/incomplete yambo runs, taking corrective
        action and resubmitting automatically. These classes of errors are taken care of:
        1. Memory probelms
        2. Parallelism problems
        3. Some input inconsistency problems (too low number of bands)
        4. Queue time exhaustion.
        The calculation is restarted upto a maximum number of 4 retries
        """
        self.report("Checking if yambo restart is needed")

        #enough restarts remaining?
        if self.ctx.restart >= self.ctx.max_restarts:
            self.report(
                "I will not restart: maximum restarts reached: {}".format(
                    self.ctx.max_restarts))
            return False

        else:
            self.report(
                "I can restart (# {}), max restarts ({}) not reached yet".format(
                    self.ctx.restart, self.ctx.max_restarts))
            calc = load_node(self.ctx.yambo_pks[-1])

        if calc.is_finished_ok:
            self.report('All went ok, I will not restart')
            return False
        else:
            self.report('Some error occurred, checking')

            if calc.is_killed:
                self.report('Killed from AiiDA for unknown reasons, we try to resubmit')
                return True

            if calc.exit_status == 100 or calc.exit_status == 103:
                self.report(
                    "Calculation {} failed or did not generate outputs for unknown reason, restarting with no changes"
                    .format(calc.pk))
                return True

            if calc.exit_status == 102:
                self.report('Something goes wrong, but we don\'t know what, so we cannot restart')
                #return self.exit_code.WORKFLOW_NOT_COMPLETED
                return False


            #timing errors
            if calc.exit_status == 101:
                max_input_seconds = self.ctx.calculation_set.get_dict(
                )['max_wallclock_seconds']
                max_input_seconds = max_input_seconds*1.3
                calculation_set = self.ctx.calculation_set.get_dict()
                calculation_set['max_wallclock_seconds'] = int(max_input_seconds)
                self.ctx.calculation_set = Dict(dict=calculation_set)
                self.report(
                    "Failed calculation, likely queue time exhaustion, restarting with new max_input_seconds = {}"
                    .format(int(max_input_seconds)))
                return True


            #para errors
            if calc.exit_status == 104:
                output_p = calc.outputs.output_parameters.get_dict()
                if len(calc.outputs.output_parameters.get_dict()['errors']) < 1:
                    # No errors, We  check for memory issues, indirectly
                    if 'last_memory_time' in list(
                            calc.outputs.output_parameters.get_dict().keys()):
                        # check if the last alloc happened close to the end:
                        last_mem_time = calc.outputs.output_parameters.get_dict()['last_memory_time']
                        if abs(last_time - last_mem_time) < 3:  # 3 seconds  selected arbitrarily,
                            # this is (based on a simple heuristic guess, a memory related problem)
                            # change the parallelization to account for this before continuing, warn user too.
                            params = self.ctx.parameters.get_dict()
                            X_all_q_CPU = params.pop('X_all_q_CPU', '')
                            X_all_q_ROLEs = params.pop('X_all_q_ROLEs', '')
                            SE_CPU = params.pop('SE_CPU', '')
                            SE_ROLEs = params.pop('SE_ROLEs', '')
                            calculation_set = self.ctx.calculation_set.get_dict(
                            )
                            params[
                                'X_all_q_CPU'], calculation_set = reduce_parallelism(
                                    'X_all_q_CPU', X_all_q_ROLEs, X_all_q_CPU,
                                    calculation_set)
                            params[
                                'SE_CPU'], calculation_set = reduce_parallelism(
                                    'SE_CPU', SE_ROLEs, SE_CPU,
                                    calculation_set)
                            params["X_all_q_ROLEs"] = X_all_q_ROLEs
                            params["SE_ROLEs"] = SE_ROLEs
                            self.ctx.calculation_set = Dict(dict=calculation_set)
                            self.ctx.parameters = Dict(
                                dict=params)
                            self.report(
                                "Calculation  {} failed likely from memory issues"
                            )
                            self.report(
                                "Old parallelism {}= {} , {} = {} ".format(
                                    X_all_q_ROLEs, X_all_q_CPU, SE_ROLEs,
                                    SE_CPU))
                            self.report(
                                "New parallelism selected {}={}, {} = {} ".
                                format(X_all_q_ROLEs, params['X_all_q_CPU'],
                                       SE_ROLEs, params['SE_CPU']))
                            return True
                        else:
                            pass

    def yambo_restart(self):
        """Submits a yambo calculation using the yambo plugin

        This function submits a calculation, usually this represents a
        resubmission of a failed calculation, or a continuation from P2Y/Init run.
        """
        self.report("Now we restart")
        calc = load_node(self.ctx.yambo_pks[-1])
        if not calc:
            raise ValidationError("restart calculations can not start: calculation no found")
            #return self.exit_code.WFL_NOT_COMPLETED

        parent_folder = calc.outputs.remote_folder
        new_settings = self.inputs.settings.get_dict()

        inputs = generate_yambo_input_params(
            self.inputs.precode, self.inputs.yambocode, parent_folder,
            self.ctx.parameters, self.ctx.calculation_set,
            Dict(dict=new_settings))
        future = self.run_yambo(inputs)
        self.ctx.yambo_pks.append(future.pk)
        self.ctx.restart += 1
        self.report(" restarting from:{}  ".format(future.pk))
        return ToContext(yambo_restart=future)

    def run_yambo(self, inputs):
        """Call submit with the inputs

        Takes some inputs and does a submit."""
        future = self.submit(YamboCalculation, **inputs)
        self.ctx.yambo_pks.append(future.pk)
        self.report(" submitted a calculation with pk = {} ".format(future.pk))
        return future  # we can not ReturnToContext since this fuction is not called from the outline


    def report_wf(self):
        """Report the outputs of the workchain

        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        calc = load_node(self.ctx.yambo_pks[-1])
#try exception
        if calc.is_finished_ok:
            self.report("workflow completed")
        else:
            self.report("workflow not completed")





if __name__ == "__main__":
    pass
