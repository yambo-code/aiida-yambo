# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys

from aiida.orm import RemoteData
from aiida.orm import Str, Dict, Int

from aiida.common import ValidationError

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit
from aiida.engine import BaseRestartWorkChain, register_process_handler, ProcessHandlerReport
from aiida_yambo.calculations.gw import YamboCalculation



class YamboRestartWf(BaseRestartWorkChain):

    """This module interacts directly with the yambo plugin to submit calculations

    This module submits calculations using the yambo plugin, and manages them, including
    restarting the calculation in case of:
    1. Memory problems (will reduce MPI parallelism before resubmitting) -- to be fixed
    2. Queue time exhaustions (will increase time by a fraction before resubmitting)
    3. Parallelism errors (will reduce the MPI the parallelism before resubmitting)  -- to be fixed
    4. Errors originating from a few select unphysical input parameters like too low bands.  -- to be fixed
    """

    @classmethod
    def define(cls, spec):

        super(YamboRestartWf, cls).define(spec)
        spec.expose_inputs(YamboCalculation, namespace='yambo', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])
        spec.input("parent_folder", valid_type=RemoteData, required=True)
        spec.input("max_walltime", valid_type=Int, default=Int(86400))



##################################### OUTLINE ####################################

        spec.outline(
            cls.setup,
            cls.validate_parameters,
            cls.validate_resources,
            cls.validate_parent,
            while_(cls.should_run_process)(
                cls.prepare_calculation,
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )


###################################################################################

        spec.output('last_calc_folder', valid_type = RemoteData,
            help='The last calculation remote folder.')

        spec.exit_code(300, 'ERROR_UNRECOVERABLE_FAILURE',
            message='The calculation failed with an unrecoverable error.')



    def setup(self):
        """setup of the calculation and run
        """
        super(YamboRestartWf, self).setup()
        # setup #
        self.ctx.inputs = self.exposed_inputs(YamboCalculation, 'yambo')

    def validate_parameters(self):
        """validation of the input parameters... including settings and the namelist...
           for example, the parallelism namelist is different from version the version... 
           we need some input helpers to fix automatically this with respect to the version of yambo
        """
    def validate_resources(self):
        """validation of machines... ecc with respect para options
        """
    def validate_parent(self):
        """validation of the parent calculation --> should be at least nscf/p2y
        """
        self.ctx.inputs['parent_folder'] = self.inputs.parent_folder

    '''
    def yambo_should_restart(self):

            if calc.exit_status == 300 or calc.exit_status == 303:
                self.report(
                    "Calculation {} failed or did not generate outputs for unknown reason, restarting with no changes"
                    .format(calc.pk))
                return True

            if calc.exit_status == 302:
                self.report('Something goes wrong, but we don\'t know what')
                new_settings =  self.ctx.inputs.settings.get_dict()
                new_settings['HARD_LINK'] = True
                self.report('Trying to hard copy the SAVE')
                self.ctx.inputs.settings = Dict(dict=new_settings) # to link the db
                return True

    def yambo_restart(self):
        """Submits a yambo calculation using the yambo plugin

        This function submits a calculation, usually this represents a
        resubmission of a failed calculation, or a continuation from P2Y/Init run.
        """

        calc = self.ctx.calc
        self.report("Now we restart")
        if not calc:
            raise ValidationError("restart calculations cannot start: calculation not found")
            #return self.exit_code.WFL_NOT_COMPLETED

        if calc.exit_status == 102:
            pass
        else:
            self.ctx.inputs.parent_folder = calc.outputs.remote_folder

        # submission of the next try #
        future = self.submit(YamboCalculation, **self.ctx.inputs)
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
        self.out('last_calc_folder', calc.outputs.remote_folder)
    '''

    def report_error_handled(self, calculation, action):
        """Report an action taken for a calculation that has failed.
        This should be called in a registered error handler if its condition is met and an action was taken.
        :param calculation: the failed calculation node
        :param action: a string message with the action taken
        """
        arguments = [calculation.process_label, calculation.pk, calculation.exit_status, calculation.exit_message]
        self.report('{}<{}> failed with exit status {}: {}'.format(*arguments))
        self.report('Action taken: {}'.format(action))

    @process_handler(YamboRestartWf, 600)
    def _handle_unrecoverable_failure(self, calculation):
        """
        Handle calculations with an exit status below 400 which are unrecoverable, 
        so abort the work chain.
        """        
        if calculation.exit_status < 400:
            self.report_error_handled(calculation, 'unrecoverable error, aborting...')
            return ProcessHandlerReport(True, True, self.exit_codes.ERROR_UNRECOVERABLE_FAILURE)
   
    @process_handler(YamboRestartWf, 580)
    def _handle_walltime_error(self, calculation, exit_code = ['WALLTIME_ERROR']):
        """
        Handle calculations for a walltime error; 
        we increase the simulation time and copy the database already created.
        """
        self.ctx.inputs.metadata.options = fix_time(self.ctx.inputs.metadata.options,\
                                                    self.ctx.iteration, self.inputs.max_walltime)
        update_dict(self.ctx.inputs.settings,'PARENT_DB',True) # to link the dbs in aiida.out
                   
        self.report_error_handled(calculation, 'walltime error detected, so we increase time: {} \
                                                seconds and copy dbs already done'\
                                                .format(int(self.ctx.inputs.metadata.options['max_wallclock_seconds'])))
        return ProcessHandlerReport(True, True)

    @process_handler(YamboRestartWf, 560)
    def _handle_parallelism_error(self, calculation, exit_code = ['PARA_ERROR']):
        """
        Handle calculations for a parallelism error; 
        we try to change the parallelism options.
        """
        new_para, self.ctx.inputs.metadata.options = fix_parallelism(self.ctx.inputs)
        update_dict(self.ctx.inputs.parameters, new_para.keys(), new.para.values())
                   
        self.report_error_handled(calculation, 'parallelism error detected, so we try to fix it')
        return ProcessHandlerReport(True, True)

    @process_handler(YamboRestartWf, 540)
    def _handle_memory_error(self, calculation, exit_code = ['MEMORY_ERROR']):
        """
        Handle calculations for a memory error; 
        we try to change the parallelism options, in particular the mpi-openmp balance.
        if cpu_per_task(mpi/node) is already set to 1, we can increase the number of nodes,
        accordingly to the inputs permissions.
        """
        new_para, self.ctx.inputs.metadata.options = fix_memory(self.ctx.inputs)
        update_dict(self.ctx.inputs.parameters, new_para.keys(), new.para.values())
                   
        self.report_error_handled(calculation, 'memory error detected, so we change nodes-mpi-openmpi balance')
        return ProcessHandlerReport(True, True)

if __name__ == "__main__":
    pass
