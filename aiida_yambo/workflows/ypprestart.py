# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import warnings

from aiida.orm import RemoteData
from aiida.orm import Str, Dict, Int, Bool, load_code

from aiida.common import ValidationError

from aiida.engine import WorkChain, while_, if_
from aiida.engine import ToContext
from aiida.engine import submit
from aiida.engine.processes.workchains.restart import BaseRestartWorkChain
from aiida.engine.processes.workchains.utils import ProcessHandlerReport, process_handler
from aiida.orm import FolderData, Str, List

from aiida_yambo.calculations.ypp import YppCalculation
from aiida_yambo.utils.parallel_namelists import *
from aiida_yambo.utils.common_helpers import *

from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

class YppRestart(ProtocolMixin, BaseRestartWorkChain):

    """This module interacts directly with the yambo plugin to submit calculations

    This module submits calculations using the yambo plugin, and manages them, including
    restarting the calculation in case of:
    1. Memory problems (will reduce MPI parallelism before resubmitting) -- to be fixed
    2. Queue time exhaustions (will increase time by a fraction before resubmitting)
    3. Parallelism errors (will reduce the MPI the parallelism before resubmitting)  -- to be fixed
    4. Errors originating from a few select unphysical input parameters like too low bands.  -- to be fixed
    """

    _process_class = YppCalculation
    _error_handler_entry_point = 'aiida_yambo.workflow_error_handlers.ypprestart'

    @classmethod
    def define(cls, spec):

        super(YppRestart, cls).define(spec)
        spec.expose_inputs(YppCalculation, namespace='ypp', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])
        spec.input("parent_folder", valid_type=RemoteData, required=False)

        spec.input(
            'pw2wannier90_parent',
            valid_type=FolderData,
            required=False,
            help=
            "the pw2wannier90 retrieved folder, that has mmn and amn files as output."
        )


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
            cls.post_processing,
            cls.results,
        )


###################################################################################

        spec.expose_outputs(YppCalculation)

        spec.exit_code(300, 'ERROR_UNRECOVERABLE_FAILURE',
            message='The calculation failed with an unrecoverable error.')
        spec.exit_code(301, 'LOW_NUMBER_OF_NSCF_BANDS',
            message='not enough bands in the Nscf dft step - nbnd - .')
        spec.exit_code(302, 'EMPTY_PARENT',
            message='parent is empty in the remote computer.')
        spec.exit_code(304, 'WANNIER90_PP_PARENT_NOT_PRESENT',
                message='Nnkp file not present')
        spec.exit_code(305, 'PW2WANNIER90_PARENT_NOT_PRESENT',
                message='mmn amn folder not present')

    @classmethod
    def get_protocol_filepath(cls):
        """Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from aiida_yambo.workflows.protocols import yambo as ypprestart_protocols
        return files(ypprestart_protocols) / 'ypprestart.yaml'
    
    @classmethod
    def get_builder_from_protocol(
        cls,
        code,
        protocol='merge_QP',
        overrides={},
        parent_folder=None,
        **_
    ):
        """Return a builder prepopulated with inputs selected according to the chosen protocol.
        :return: a process builder instance with all inputs defined ready for launch.
        """
        from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

        if isinstance(code, str):           
            code = load_code(code)

        inputs = cls.get_protocol_inputs(protocol, overrides={})

        meta_parameters = inputs.pop('meta_parameters', None)


        # Update the parameters based on the protocol inputs
        parameters = inputs['ypp']['parameters']
        metadata = inputs['ypp']['metadata']

        # If overrides are provided, they are considered absolute
        if overrides:
            parameter_arguments_overrides = overrides.get('ypp', {}).get('parameters', {}).get('arguments', [])
            parameters['arguments'] += parameter_arguments_overrides
            
            parameter_variables_overrides = overrides.get('ypp', {}).get('parameters', {}).get('variables', {})
            parameters['variables'] = recursive_merge(parameters['variables'], parameter_variables_overrides)

            metadata_overrides = overrides.get('metadata', {})
            metadata = recursive_merge(metadata, metadata_overrides)

        print('Summary of the inputs:{}\n'\
            .format(parameters))

        builder = cls.get_builder()
        builder.ypp['code'] = code
        builder.ypp['parameters'] = Dict(parameters)
        builder.ypp['metadata'] = metadata
        if 'settings' in inputs['ypp']:
            builder.ypp['settings'] = Dict(inputs['ypp']['settings'])
        builder.clean_workdir = Bool(inputs['clean_workdir'])

        if not parent_folder:
            warnings.warn('You must provide a parent folder calculation, either YPP or YAMBO') 
        elif isinstance(parent_folder,str):
            pass
        else:
            builder.parent_folder = parent_folder
        # pylint: enable=no-member

        return builder

    def setup(self):
        """setup of the calculation and run
        """
        super(YppRestart, self).setup()
        # setup #
        self.ctx.inputs = self.exposed_inputs(YppCalculation, 'ypp')

    def validate_parameters(self):
        """validation of the input parameters... including settings and the namelist...
           for example, the parallelism namelist is different from version the version... 
           we need some input helpers to fix automatically this with respect to the version of yambo
        """
        pass

    def validate_resources(self):
        """validation of machines... completeness and with respect para options
        """
        pass

    def validate_parent(self):
        """validation of the parent calculation --> should be at least nscf/p2y
        """
        self.ctx.inputs['parent_folder'] = self.inputs.parent_folder
        if self.ctx.inputs['parent_folder'].is_empty: 
            return self.exit_codes.EMPTY_PARENT

    def should_run_ypp(self):
        """understand if it is only a post processing of ypp or you need 
        also to run a YppCalculation
        """
        self.ctx.parent_calc = take_calc_from_remote(self.ctx.inputs['parent_folder'])
        if self.ctx.parent_calc.process_type=='aiida.calculations:yambo.ypp':
            if self.ctx.parent_calc.is_finished_ok:
                self.report('We do not run YppCalculation')
                return False
            else:
                return True #should be an error exit status
        elif self.ctx.parent_calc.process_type=='aiida.calculations:yambo.yambo':
            return True

    def post_processing(self):

        try:
            calculation = self.ctx.children[self.ctx.iteration - 1]
        except:
            calculation = self.ctx.parent_calc
        
        if hasattr(self.inputs,'pw2wannier90_parent'):
            self.report('running gw2wannier90, folders are:\n output_ypp: {}\n output_pw2wannier90: {}\n'.format(calculation.outputs.retrieved._repository._repo_folder.abspath+'/path/',
            self.inputs.pw2wannier90_parent._repository._repo_folder.abspath+'/path/'))
            gw2wannier90(
                    seedname=Str('aiida'), 
                    options = List(list=['mmn','amn']), 
                    output_path=Str(calculation.outputs.retrieved._repository._repo_folder.abspath+'/path/'),
                    #nnkp_file = calculation.inputs.nnkp_file, 
                    pw2wannier_parent = self.inputs.pw2wannier90_parent,
                )
            self.report('gw2wannier90 run, output folder = {}'.format(calculation.outputs.retrieved._repository._repo_folder.abspath+'/path/'))
        return

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
    
    @process_handler(priority = 559, exit_codes = [YppCalculation.exit_codes.MERGE_NOT_COMPLETE])
    def _handle_walltime_error(self, calculation):
        """
        Handle calculations for a walltime error; 
        we increase the simulation time and copy the database already created.
        """
        
        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        if hasattr(self.ctx.inputs,'QP_calculations'): del self.ctx.inputs.QP_calculations
                
        self.report_error_handled(calculation, 'merge not completed error, so we try to finish it')
        return ProcessHandlerReport(True)
