# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys

from aiida.orm import RemoteData
from aiida.orm import Str, Dict, Int

from aiida.common import ValidationError

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit
from aiida.engine.processes.workchains.restart import BaseRestartWorkChain
from aiida.engine.processes.workchains.utils import ProcessHandlerReport, process_handler

from aiida_yambo.calculations.yambo import YamboCalculation
from aiida_yambo.workflows.utils.helpers_yamborestart import *
from aiida_yambo.utils.parallel_namelists import*


class YamboRestart(BaseRestartWorkChain):

    """This module interacts directly with the yambo plugin to submit calculations

    This module submits calculations using the yambo plugin, and manages them, including
    restarting the calculation in case of:
    1. Memory problems (will reduce MPI parallelism before resubmitting) -- to be fixed
    2. Queue time exhaustions (will increase time by a fraction before resubmitting)
    3. Parallelism errors (will reduce the MPI the parallelism before resubmitting)  -- to be fixed
    4. Errors originating from a few select unphysical input parameters like too low bands.  -- to be fixed
    """

    _process_class = YamboCalculation
    _error_handler_entry_point = 'aiida_yambo.workflow_error_handlers.yamborestart'

    @classmethod
    def define(cls, spec):

        super(YamboRestart, cls).define(spec)
        spec.expose_inputs(YamboCalculation, namespace='yambo', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])
        spec.input("parent_folder", valid_type=RemoteData, required=True)
        spec.input("max_walltime", valid_type=Int, default=lambda: Int(86400))
        spec.input("code_version", valid_type=Str, default=lambda: Str('4.5'))


##################################### OUTLINE ####################################

        spec.outline(
            cls.setup,
            cls.validate_parameters,
            cls.validate_resources,
            cls.validate_parent,
            while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
            ),
            cls.results,
        )


###################################################################################

        spec.expose_outputs(YamboCalculation)
        
        spec.exit_code(300, 'ERROR_UNRECOVERABLE_FAILURE',
            message='The calculation failed with an unrecoverable error.')

    def setup(self):
        """setup of the calculation and run
        """
        super(YamboRestart, self).setup()
        # setup #
        self.ctx.inputs = self.exposed_inputs(YamboCalculation, 'yambo')

    def validate_parameters(self):
        """validation of the input parameters... including settings and the namelist...
           for example, the parallelism namelist is different from version the version... 
           we need some input helpers to fix automatically this with respect to the version of yambo
        """
        new_para = check_para_namelists(self.ctx.inputs.parameters.get_dict(), self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()))
            self.report('adjusting parallelism namelist... please check yambo documentation')

    def validate_resources(self):
        """validation of machines... completeness and with respect para options
        """
        pass

    def validate_parent(self):
        """validation of the parent calculation --> should be at least nscf/p2y
        """
        self.ctx.inputs['parent_folder'] = self.inputs.parent_folder

    def report_error_handled(self, calculation, action):
        """Report an action taken for a calculation that has failed.
        This should be called in a registered error handler if its condition is met and an action was taken.
        :param calculation: the failed calculation node
        :param action: a string message with the action taken
        """
        arguments = [calculation.process_label, calculation.pk, calculation.exit_status, calculation.exit_message]
        self.report('{}<{}> failed with exit status {}: {}'.format(*arguments))
        self.report('Action taken: {}'.format(action))

    @process_handler(priority = 600)
    def _handle_unrecoverable_failure(self, calculation):
        """
        Handle calculations with an exit status below 400 which are unrecoverable, 
        so abort the work chain.
        """        
        if calculation.exit_status < 400 and not calculation.is_finished_ok:
            self.report_error_handled(calculation, 'unrecoverable error, aborting...')
            return ProcessHandlerReport(True, self.exit_codes.ERROR_UNRECOVERABLE_FAILURE)
   
    @process_handler(priority = 580, exit_codes = [YamboCalculation.exit_codes.WALLTIME_ERROR])
    def _handle_walltime_error(self, calculation):
        """
        Handle calculations for a walltime error; 
        we increase the simulation time and copy the database already created.
        """
        
        self.ctx.inputs.metadata.options = fix_time(self.ctx.inputs.metadata.options,self.ctx.iteration, self.inputs.max_walltime)
        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        
        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs'] :
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO', True) # to link the dbs in aiida.out 
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', False)                   
        
        self.report_error_handled(calculation, 'walltime error detected, so we increase time: {} \
                                                seconds and link outputs'\
                                                .format(int(self.ctx.inputs.metadata.options['max_wallclock_seconds'])))
        return ProcessHandlerReport(True)

    @process_handler(priority =  560, exit_codes = [YamboCalculation.exit_codes.PARA_ERROR])
    def _handle_parallelism_error(self, calculation):
        """
        Handle calculations for a parallelism error; 
        we try to change the parallelism options.
        """
        new_para, new_resources  = fix_parallelism(self.ctx.inputs.metadata.options.resources, calculation)
        self.ctx.inputs.metadata.options.resources = new_resources
        self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()))

        new_para = check_para_namelists(new_para, self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()))
            self.report('adjusting parallelism namelist... please check yambo documentation')

        
        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs'] :
            self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO',True) # to link the dbs in aiida.out
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', False)                   



        self.report_error_handled(calculation, 'parallelism error detected, so we try to fix it')
        return ProcessHandlerReport(True)

    @process_handler(priority =  540, exit_codes = [YamboCalculation.exit_codes.MEMORY_ERROR, \
                                                    YamboCalculation.exit_codes.X_par_MEMORY_ERROR])
    def _handle_memory_error(self, calculation):
        """
        Handle calculations for a memory error; 
        we try to change the parallelism options, in particular the mpi-openmp balance.
        if cpu_per_task(mpi/node) is already set to 1, we can increase the number of nodes,
        accordingly to the inputs permissions.
        """
        new_para, new_resources  = fix_memory(self.ctx.inputs.metadata.options.resources, calculation, calculation.exit_status)
        self.ctx.inputs.metadata.options.resources = new_resources
        self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()))

            
        new_para = check_para_namelists(new_para, self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()))
            self.report('adjusting parallelism namelist... please check yambo documentation')


        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs'] :
            self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO',True) # to link the dbs in aiida.out
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', False)                   

        self.report_error_handled(calculation, 'memory error detected, so we change mpi-openmpi balance')
        return ProcessHandlerReport(True)