# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import warnings

from aiida.orm import RemoteData
from aiida.orm import Str, Dict, Int, Bool, StructureData

from aiida.common import ValidationError

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit
from aiida.engine.processes.workchains.restart import BaseRestartWorkChain
from aiida.engine.processes.workchains.utils import ProcessHandlerReport, process_handler

from aiida_yambo.calculations.yambo import YamboCalculation
from aiida_yambo.workflows.utils.helpers_yamborestart import *
from aiida_yambo.utils.parallel_namelists import *
from aiida_yambo.utils.defaults.create_defaults import *
from aiida_yambo.utils.common_helpers import *

from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

class YamboRestart(ProtocolMixin, BaseRestartWorkChain):

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
        spec.input("parent_folder", valid_type=RemoteData, required=False) #false to build the ywfl protocols
        spec.input("max_walltime", valid_type=Int, default=lambda: Int(86400))
        spec.input("max_number_of_nodes", valid_type=Int, default=lambda: Int(0),
                    help = 'max number of nodes for restarts; if 0, it does not increase the number of nodes')
        spec.input("code_version", valid_type=Str, default=lambda: Str('5.x'))


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
        spec.exit_code(301, 'LOW_NUMBER_OF_NSCF_BANDS',
            message='not enough bands in the Nscf dft step - nbnd - .')
        spec.exit_code(302, 'EMPTY_PARENT',
            message='parent is empty in the remote computer.')
        spec.exit_code(303, 'NO_PARENT',
            message='parent is not provided.')
    
    @classmethod
    def get_protocol_filepath(cls):
        """Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from aiida_yambo.workflows.protocols import yambo as yamborestart_protocols
        return files(yamborestart_protocols) / 'yamborestart.yaml'
    
    @classmethod
    def get_builder_from_protocol(
        cls,
        preprocessing_code,
        code,
        protocol='fast',
        overrides={},
        parent_folder=None,
        NLCC=False,
        RIM_v=False,
        RIM_W=False,
        **_
    ):
        """Return a builder prepopulated with inputs selected according to the chosen protocol.
        :return: a process builder instance with all inputs defined ready for launch.
        """
        from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

        if isinstance(code, str):
            
            preprocessing_code = orm.load_code(preprocessing_code)
            code = orm.load_code(code)

        inputs = cls.get_protocol_inputs(protocol, overrides={})

        meta_parameters = inputs.pop('meta_parameters')

        try:
            pw_parent = find_pw_parent(take_calc_from_remote(parent_folder,level=-1))
            PW_cutoff = pw_parent.inputs.parameters.get_dict()['SYSTEM']['ecutwfc']
            nelectrons = int(pw_parent.outputs.output_parameters.get_dict()['number_of_electrons'])
        except:
            nelectrons, PW_cutoff = overrides.pop('nelectrons',0), overrides.pop('PW_cutoff',0)

        # Update the parameters based on the protocol inputs
        parameters = inputs['yambo']['parameters']
        metadata = inputs['yambo']['metadata']

        # NLCC check:
        if NLCC and not 'NLCC' in parameters['arguments']:
            parameters['arguments'].append('NLCC')
        
        # RIM_v check:
        if RIM_v and not 'rim_cut' in parameters['arguments']:
            parameters['arguments'].append('rim_cut')
            parameters['variables']['RandQpts'] = [5000000, '']
            parameters['variables']['RandGvec'] = [100, 'RL']

        # RIM_W check:
        if RIM_W and not 'RIM_W' in parameters['arguments']:
            parameters['arguments'].append('RIM_W')
            parameters['variables']['CUTGeo'] = 'slab Z'
            parameters['variables']['RandGvecW'] = [13, 'RL']

        #if protocols GW
        screening_PW_cutoff = int(PW_cutoff*meta_parameters['ratio_PW_cutoff'])
        screening_PW_cutoff -= screening_PW_cutoff%2 
        parameters['variables']['NGsBlkXp'] = [max(1,screening_PW_cutoff),'Ry']
        
        bands = int(nelectrons * meta_parameters['ratio_bands_electrons']/2) #want something also Volume dependent.

        parameters['variables']['BndsRnXp'] = [[1, bands], '']
        parameters['variables']['GbndRnge'] = parameters['variables']['BndsRnXp']

        if 'bse' in protocol:
            parameters['variables']['BndsRnXs'] = parameters['variables'].pop('BndsRnXp')
            parameters['variables']['NGsBlkXs'] = parameters['variables'].pop('NGsBlkXp')
            parameters['variables']['BSENGBlk'] = parameters['variables']['NGsBlkXs']

        # If overrides are provided, they are considered absolute
        if overrides:
            parameter_arguments_overrides = overrides.get('yambo', {}).get('parameters', {}).get('arguments', [])
            parameters['arguments'] += parameter_arguments_overrides
            
            parameter_variables_overrides = overrides.get('yambo', {}).get('parameters', {}).get('variables', {})
            parameters['variables'] = recursive_merge(parameters['variables'], parameter_variables_overrides)

            metadata_overrides = overrides.get('metadata', {})
            metadata = recursive_merge(metadata, metadata_overrides)

        if not 'QPkrange' in parameters['variables'].keys() and 'gw0' in parameters['arguments']:
            parameters['variables']['QPkrange'] = [[[1, 1, 32, 32,]], ''] #fictitious

        print('Summary of the main inputs:\nBndsRnXp = {}\nGbndRnge = {}\nNGsBlkXp = {} {}\n'\
            .format(parameters['variables']['BndsRnXp'][0][1],parameters['variables']['GbndRnge'][0][1],parameters['variables']['NGsBlkXp'][0],parameters['variables']['NGsBlkXp'][1]))

        builder = cls.get_builder()
        builder.yambo['preprocessing_code'] = preprocessing_code
        builder.yambo['code'] = code
        builder.yambo['parameters'] = Dict(dict=parameters)
        builder.yambo['metadata'] = metadata
        if 'settings' in inputs['yambo']:
            builder.yambo['settings'] = Dict(dict=inputs['yambo']['settings'])
        builder.clean_workdir = Bool(inputs['clean_workdir'])

        if not parent_folder:
            warnings.warn('You must provide a parent folder calculation, either QE or YAMBO')
        elif isinstance(parent_folder,str):
            pass
        else:
            builder.parent_folder = parent_folder
        # pylint: enable=no-member

        return builder
    
    #############################################################################
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
        new_para = check_para_namelists(self.ctx.inputs.parameters.get_dict()['variables'], self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()),sublevel='variables')
            self.report('adjusting parallelism namelist... please check yambo documentation')
        
        try:
            nscf_parent = find_pw_parent(take_calc_from_remote(self.inputs.parent_folder,level=-1))
        except:
            nscf_parent = take_calc_from_remote(self.inputs.parent_folder,level=-1)
        yambo_bandsX = self.ctx.inputs.parameters.get_dict()['variables'].pop('BndsRnXp',[[0],''])[0][-1]
        yambo_bandsSc = self.ctx.inputs.parameters.get_dict()['variables'].pop('GbndRnge',[[0],''])[0][-1]

        if nscf_parent.inputs.parameters.get_dict()['SYSTEM']['nbnd'] < max(yambo_bandsX,yambo_bandsSc):
            self.report('You must run an nscf with nbnd at least =  {}'.format(max(yambo_bandsX,yambo_bandsSc)))
            return self.exit_codes.LOW_NUMBER_OF_NSCF_BANDS


    def validate_resources(self):
        """validation of machines... completeness and with respect para options
        """
        pass

    def validate_parent(self):
        """validation of the parent calculation --> should be at least nscf/p2y
        """
        if not hasattr(self.inputs,'parent_folder'):
            return self.exit_codes.NO_PARENT
        else:
            self.ctx.inputs['parent_folder'] = self.inputs.parent_folder
        try: #sometimes "Authentication timeout".
            if self.ctx.inputs['parent_folder'].is_empty: 
                return self.exit_codes.EMPTY_PARENT
        except:
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
   
    @process_handler(priority = 590, exit_codes = [YamboCalculation.exit_codes.NO_SUCCESS])
    def _handle_walltime_error(self, calculation):
        """
        Handle calculations for an unknown reason; 
        we copy the SAVE already created, if any.
        """
        
        self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_SAVE', True)                   
        
        self.report_error_handled(calculation, 'Trying to copy the SAVE folder and restart')
        return ProcessHandlerReport(True)
    
    
    @process_handler(priority = 559, exit_codes = [YamboCalculation.exit_codes.WALLTIME_ERROR])
    def _handle_walltime_error(self, calculation):
        """
        Handle calculations for a walltime error; 
        we increase the simulation time and copy the database already created.
        """
        
        self.ctx.inputs.metadata.options = fix_time(self.ctx.inputs.metadata.options, self.ctx.iteration, self.inputs.max_walltime)
        self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
        
        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs']:
            #self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO', True) # to link the dbs in aiida.out 
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', True)                   
        
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
        new_para, new_resources, pop_list  = fix_parallelism(self.ctx.inputs.metadata.options.resources, calculation)
        self.ctx.inputs.metadata.options.resources = new_resources
        self.ctx.inputs.metadata.options.prepend_text =self.ctx.inputs.metadata.options.prepend_text + "\nexport OMP_NUM_THREADS="+str(new_resources['num_cores_per_mpiproc'])
        self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()), sublevel='variables',pop_list= pop_list)

        '''new_para = check_para_namelists(new_para, self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()),sublevel='variables')
            self.report('adjusting parallelism namelist... please check yambo documentation')'''

        
        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs']:
            self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
            #self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO',True) # to link the dbs in aiida.out
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', True)                   



        self.report_error_handled(calculation, 'parallelism error detected, so we try to fix it setting PAR_def_mode= "balanced"')
        return ProcessHandlerReport(True)

    @process_handler(priority =  561, exit_codes = [YamboCalculation.exit_codes.MEMORY_ERROR, \
                                                    YamboCalculation.exit_codes.X_par_MEMORY_ERROR])
    def _handle_memory_error(self, calculation):
        """
        Handle calculations for a memory error; 
        we try to change the parallelism options, in particular the mpi-openmp balance.
        if cpu_per_task(mpi/node) is already set to 1, we can increase the number of nodes,
        accordingly to the inputs permissions.
        """
        new_para, new_resources, pop_list  = fix_memory(self.ctx.inputs.metadata.options.resources, calculation, calculation.exit_status,
                                                self.inputs.max_number_of_nodes, self.ctx.iteration)
        self.ctx.inputs.metadata.options.resources = new_resources
        self.ctx.inputs.metadata.options.prepend_text =self.ctx.inputs.metadata.options.prepend_text + "\nexport OMP_NUM_THREADS="+str(new_resources['num_cores_per_mpiproc'])
        self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()),sublevel='variables',pop_list= pop_list)

            
        '''new_para = check_para_namelists(new_para, self.inputs.code_version.value)
        if new_para:
            self.ctx.inputs.parameters = update_dict(self.ctx.inputs.parameters, list(new_para.keys()), list(new_para.values()),sublevel='variables')
            self.report('adjusting parallelism namelist... please check yambo documentation')'''


        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs']:
            self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
            #self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'RESTART_YAMBO',True) # to link the dbs in aiida.out
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', True)                   

        self.report_error_handled(calculation, 'memory error detected, so we change mpi-openmpi balance and set PAR_def_mode= "balanced"')
        return ProcessHandlerReport(True)

    @process_handler(priority =  562, exit_codes = [YamboCalculation.exit_codes.Variable_NOT_DEFINED])
    def _handle_variable_NOT_DEFINED(self, calculation):
        """
        Handle calculations Variable NOT DEFINED error, happens with ndb.pp_fragments.
        redo the calculation, trying to delete the wrong fragment and recompute it.
        """

        #self.ctx.inputs.metadata.options.prepend_text = "export OMP_NUM_THREADS="+str(new_resources['num_cores_per_mpiproc'])

        if calculation.outputs.output_parameters.get_dict()['yambo_wrote_dbs']:
            corrupted_fragment = calculation.outputs.output_parameters.get_dict()['corrupted_fragment']
            self.ctx.inputs.parent_folder = calculation.outputs.remote_folder
            self.ctx.inputs.metadata.options.prepend_text =self.ctx.inputs.metadata.options.prepend_text + "\nrm aiida.out/"+str(corrupted_fragment)
            self.ctx.inputs.settings = update_dict(self.ctx.inputs.settings,'COPY_DBS', True)                   

        self.report_error_handled(calculation, 'Variable NOT DEFINED error detected, so we restart and recompute the corrupted fragment')
        return ProcessHandlerReport(True)
