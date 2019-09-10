# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
from collections import defaultdict

from aiida.orm import CalcJobNode
from aiida.orm import RemoteData
from aiida.orm import Code
from aiida.orm import StructureData
from aiida.orm import Float, Str, NumericType, Dict, Int, Bool
from aiida.orm import load_node

from aiida.common import InputValidationError, ValidationError
from aiida.common.links import LinkType
from aiida.common import CalcJobState, AttributeDict


from aiida.plugins import DataFactory, CalculationFactory, WorkflowFactory

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext, calcfunction
from aiida.engine import run, submit

from aiida_yambo.calculations.gw import YamboCalculation

YamboCalculation = CalculationFactory('yambo.yambo') #needed???don't think so
#YamboRestartWf = WorkflowFactory('yambo.workflow. ')

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

        super(YamboRestartWf, cls).define(spec)
        spec.expose_inputs(YamboCalculation, namespace='gw')

        spec.input("max_restarts", valid_type=Int, required=False) #key: 'max_restarts'


##################################### OUTLINE ####################################

        spec.outline(
            cls.yambobegin,
            while_(cls.yambo_should_restart)(
                cls.yambo_restart),
            cls.report_wf,
        )


###################################################################################

        spec.output('last_calc_pk', valid_type=Int,
            help='The last calculation.')

        #spec.exit_code(201, 'WORKFLOW_NOT_COMPLETED',message='Workflow failed')



    def yambobegin(self):
        """setup of the calculation and run
        """

        self.ctx.restart = 0

        # setup #

        self.ctx.inputs = self.exposed_inputs(YamboCalculation, 'gw')

        if not isinstance(self.ctx.inputs.parent_folder, RemoteData):
            raise InputValidationError("parent_folder must be of"
                                       " type RemoteData")

        #timing corrections -> minimum 5 minutes? must be here

        from aiida_yambo.workflows.utils.inp_gen import generate_yambo_inputs
        inputs = generate_yambo_inputs(**self.ctx.inputs)

        # submission of the first try #
        future = self.submit(YamboCalculation, **inputs)
        self.report("Workflow started, submitted process with pk = {}".format(future.pk))
        self.ctx.restart += 1

        return ToContext(calc = future)



    def yambo_should_restart(self):

        """This function encodes the logic to restart calculations from failures
        """
        calc = self.ctx.calc
        self.report("Checking if yambo restart is needed")

        ### check of the number of restarts ###
        if self.ctx.restart >= self.inputs.max_restarts:
            self.report(
                "I will not restart: maximum restarts reached: {}".format(
                    self.inputs.max_restarts))
            return False

        else:
            self.report(
                "I can restart (# {}), max restarts ({}) not reached yet".format(
                    self.ctx.restart, self.inputs.max_restarts))

        ### check if the calculation is failed ###
        if calc.is_finished_ok:
            self.report('All went ok, I will not restart')
            return False

        else:
            self.report('Some error occurred, checking')

        ### error check ###
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
                return False



            # timing errors #
            if calc.exit_status == 101:
                self.ctx.inputs.metadata.options['max_wallclock_seconds'] = \
                                        self.ctx.inputs.metadata.options['max_wallclock_seconds']*1.3*self.ctx.restart

                self.report(
                    "Failed calculation, likely queue time exhaustion, restarting with new max_input_seconds = {}"
                    .format(int(self.ctx.inputs.metadata.options['max_wallclock_seconds'])))
                return True


            # parallelization errors # but there should be something already in yambo...but not mpi-openmpi balance #
            if calc.exit_status == 104:
                #self.something = parallelism_optimization(self.ctx.metadata.options)
                self.report("Calculation {} failed likely from memory issues".format(calc))
                return False



    def yambo_restart(self):
        """Submits a yambo calculation using the yambo plugin

        This function submits a calculation, usually this represents a
        resubmission of a failed calculation, or a continuation from P2Y/Init run.
        """

        calc = self.ctx.calc
        self.report("Now we restart with new inputs")
        if not calc:
            raise ValidationError("restart calculations can not start: calculation no found")
            return self.exit_code.WFL_NOT_COMPLETED

        self.ctx.inputs.parent_folder = calc.outputs.remote_folder

        inputs = generate_yambo_inputs(**self.ctx.inputs)

        # submission of the next try #
        future = self.submit(YamboCalculation, **inputs)
        self.report("Workflow started, submitted process with pk = {}".format(future.pk))
        self.ctx.restart += 1

        return ToContext(calc = future)



    def report_wf(self):
        """Report the outputs of the workchain

        Output final quantities
        return information that may be used to figure out
        the status of the calculation.
        """
        calc = self.ctx.calc
        self.report("workflow completed successfully: {}, last calculation was <{}>".format(calc.is_finished_ok, calc.pk))
        self.out('last_calc_pk', calc.pk)


if __name__ == "__main__":
    pass
