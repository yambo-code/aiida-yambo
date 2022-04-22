# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

import time

#if aiida_calcs:
from aiida.orm import Dict, Str, Bool, KpointsData, RemoteData, List, load_node, Group, load_group

from aiida.engine import WorkChain, while_ , if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.common.types import ElectronicType, SpinType

from aiida.plugins import WorkflowFactory
from aiida_yambo.workflows.utils.helpers_aiida_yambo import *
from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
from aiida_yambo.workflows.utils.helpers_workflow import *
from aiida_yambo.utils.common_helpers import *
from aiida_yambo.workflows.utils.helpers_yambowf import *

from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

YamboWorkflow = WorkflowFactory('yambo.yambo.yambowf')

class YamboConvergence(ProtocolMixin, WorkChain):

    """This workflow will perform yambo convergences with respect to some parameter. It can be used also to run multi-parameter
       calculations.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl', namespace_options={'required': True})

        spec.input('precalc_inputs', valid_type=Dict, required = False)

        spec.input("parameters_space", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max iterations')
        spec.input("workflow_settings", valid_type=Dict, required=True, \
                    help = 'settings for the workflow: type, quantity to be examinated...') #there should be a default
        spec.input("parallelism_instructions", valid_type=Dict, required=False, \
                    help = 'indications for the parallelism to be used wrt values of the parameters.')
        spec.input("group_label", valid_type=Str, required=False, \
                    help = 'group of calculations already done for this system.')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.has_to_continue)(
                    if_(cls.pre_needed)(
                    cls.do_pre,
                    cls.prepare_calculations),
                    cls.next_step,
                    cls.data_analysis),
                    cls.report_wf,
                    )

##################################################################################
        spec.expose_outputs(YamboWorkflow) #the last calculation
        spec.output('history', valid_type = Dict, help='all calculations')
        spec.output('infos', valid_type = Dict, help='infos on the convergence', required = False)
        spec.output('remaining_iter', valid_type = List,  required = False, help='remaining convergence iter')       

        spec.exit_code(300, 'UNDEFINED_STATE',
                             message='The workchain is in an undefined state.') 
        spec.exit_code(301, 'PRECALC_FAILED',
                             message='The workchain failed the precalc step.')    
        spec.exit_code(302, 'CALCS_FAILED',
                             message='The workchain failed some calculations.')       
        spec.exit_code(303, 'SPACE_TOO_SMALL',
                             message='The workchain failed because the space is too small.')                           
        spec.exit_code(400, 'CONVERGENCE_NOT_REACHED',
                             message='The workchain failed to reach convergence.')

    @classmethod
    def get_protocol_filepath(cls):
        """Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from aiida_yambo.workflows.protocols import yambo as yamboconvergence_protocols
        return files(yamboconvergence_protocols) / 'yamboconvergence.yaml'
    
    @classmethod
    def get_builder_from_protocol(
        cls,
        pw_code,
        preprocessing_code,
        code,
        protocol_qe='moderate',
        protocol='moderate',
        structure=None,
        overrides={},
        NLCC=False,
        RIM_v=False,
        RIM_W=False,
        parent_folder=None,
        electronic_type=ElectronicType.INSULATOR,
        spin_type=SpinType.NONE,
        initial_magnetic_moments=None,
        **_
    ):
        """Return a builder prepopulated with inputs selected according to the chosen protocol.
        :return: a process builder instance with all inputs defined ready for launch.
        """
        from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

        if isinstance(code, str):
            
            pw_code = orm.load_code(pw_code)
            preprocessing_code = orm.load_code(preprocessing_code)
            code = orm.load_code(code)

        if electronic_type not in [ElectronicType.METAL, ElectronicType.INSULATOR]:
            raise NotImplementedError(f'electronic type `{electronic_type}` is not supported.')

        if spin_type not in [SpinType.NONE, SpinType.COLLINEAR]:
            raise NotImplementedError(f'spin type `{spin_type}` is not supported.')

        if overrides is None:
            overrides = {}
        inputs = cls.get_protocol_inputs(protocol, overrides=overrides)

        meta_parameters = inputs.pop('meta_parameters',{})
        
        builder = cls.get_builder()

        overrides_ywfl = overrides.pop('ywfl',{})

        overrides_ywfl['clean_workdir'] = overrides_ywfl.pop('clean_workdir',False)

        #########YWFL PROTOCOLS 
        builder.ywfl = YamboWorkflow.get_builder_from_protocol(
                pw_code,
                preprocessing_code,
                code,
                structure=structure,
                protocol_qe=protocol_qe,
                protocol=protocol,
                overrides=overrides_ywfl,
                NLCC=NLCC,
                RIM_v=RIM_v,
                RIM_W=RIM_W,
                electronic_type=electronic_type,
                spin_type=spin_type,
                initial_magnetic_moments=initial_magnetic_moments,
                parent_folder=parent_folder,
                )

        ######### convergence settings

        ################ K mesh
        builder.ywfl['nscf']['kpoints'] = KpointsData()
        builder.ywfl['nscf']['kpoints'].set_cell_from_structure(builder.ywfl['nscf']['pw']['structure'])

        builder.ywfl['nscf']['kpoints'].set_kpoints_mesh_from_density(meta_parameters['kmesh_density']['max'],force_parity=True)
        k_end = builder.ywfl['nscf']['kpoints'].get_kpoints_mesh()[0]
        
        builder.ywfl['nscf']['kpoints'].set_kpoints_mesh_from_density(meta_parameters['kmesh_density']['stop'],force_parity=True)
        k_stop = builder.ywfl['nscf']['kpoints'].get_kpoints_mesh()[0]

        builder.ywfl['nscf']['kpoints'].set_kpoints_mesh_from_density(meta_parameters['kmesh_density']['start'],force_parity=True)
        k_start = builder.ywfl['nscf']['kpoints'].get_kpoints_mesh()[0]
        
        k_delta = np.zeros(3,dtype='int64')
        k_delta[np.where(builder.ywfl['nscf']['pw']['structure'].pbc)] = int(meta_parameters['kmesh_density']['delta'])
        k_delta = list(k_delta)

        ################ Bands
        b_start=meta_parameters['bands']['start']
        b_stop=meta_parameters['bands']['stop']
        b_max=meta_parameters['bands']['max']
        b_delta=meta_parameters['bands']['delta']

        yambo_parameters = builder.ywfl['yres']['yambo']['parameters'].get_dict()
        for b in ['BndsRnXp','GbndRnge']:
            yambo_parameters['variables'][b] = [[1,b_start],'']
        
        ################ G cutoff
        G_start=meta_parameters['G_vectors']['start']
        G_stop=meta_parameters['G_vectors']['stop']
        G_max=meta_parameters['G_vectors']['max']
        G_delta=meta_parameters['G_vectors']['delta']

        yambo_parameters['variables']['NGsBlkXp'] = [G_start,'Ry']

        builder.ywfl['yres']['yambo']['parameters'] = Dict(dict=yambo_parameters)

        builder.parameters_space =  List(list=[  {
                           'var':['kpoint_mesh'],
                           'start': k_start,
                           'stop': k_stop ,
                           'delta': k_delta,
                           'max':k_end,
                           'steps': 4, 
                           'max_iterations': 4, \
                           'conv_thr': meta_parameters['conv_thr_k'],
                           'conv_thr_units':'%',
                           'convergence_algorithm':'new_algorithm_1D',
                           },  
                           
                           {
                           'var':['BndsRnXp','GbndRnge','NGsBlkXp'],
                           'start': [b_start,b_start,G_start],
                           'stop':[b_stop,b_stop,G_stop] ,
                           'delta':[b_delta,b_delta,G_delta],
                           'max':[b_max,b_max,G_max],
                           'steps': 6, 
                           'max_iterations': 8, \
                           'conv_thr': meta_parameters['conv_thr_bG'],
                           'conv_thr_units':'%',
                           'convergence_algorithm':'new_algorithm_2D',
                           },
                        
                        ])
        
        builder.workflow_settings = Dict(dict=inputs['workflow_settings'])

        return builder
        
    def start_workflow(self):
        """Initialize the workflow"""
        self.ctx.small_space = False
        self.ctx.ratio = []   #ratio between Ecut and EmaxC
        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')        
        self.ctx.remaining_iter = self.inputs.parameters_space.get_list()
        self.ctx.remaining_iter.reverse()
        self.ctx.hint = {}
        self.ctx.workflow_settings = self.inputs.workflow_settings.get_dict()
        self.ctx.how_bands = self.ctx.workflow_settings.pop('bands_nscf_update', 0)
        self.ctx.workflow_manager = convergence_workflow_manager(self.inputs.parameters_space,
                                                                self.ctx.workflow_settings,
                                                                self.ctx.calc_inputs.yres.yambo.parameters.get_dict(), 
                                                                self.ctx.calc_inputs.nscf.kpoints,
                                                                )

        if hasattr(self.ctx.calc_inputs,'additional_parsing'):
            l = self.ctx.workflow_settings['what']+self.ctx.calc_inputs.additional_parsing.get_list()
            self.ctx.calc_inputs.additional_parsing = List(list=list(dict.fromkeys(l)))
        else:
            self.ctx.calc_inputs.additional_parsing = List(list=list(self.ctx.workflow_settings['what']))

        if hasattr(self.inputs, "group_label"):
            self.ctx.workflow_manager['group'] = load_group(self.inputs.group_label.value)
            self.report('group: {}'.format(self.inputs.group_label.value))
        else:
            try:
                self.ctx.workflow_manager['group'] = load_group("convergence_tests_{}".format(self.ctx.calc_inputs.scf.pw.structure.get_formula()))
            except:
                self.ctx.workflow_manager['group'] = Group(label="convergence_tests_{}".format(self.ctx.calc_inputs.scf.pw.structure.get_formula()))
                self.report('creating group: {}'.format(self.ctx.calc_inputs.scf.pw.structure.get_formula()))
            if not self.ctx.workflow_manager['group'].is_stored: self.ctx.workflow_manager['group'].store()
            #here shold be added the YC to the group, not the single YWFLS
        
        if hasattr(self.inputs, "parallelism_instructions"):
            self.ctx.workflow_manager['parallelism_instructions'] = build_parallelism_instructions(self.inputs.parallelism_instructions.get_dict(),)
            #self.report('para instr: {}'.format(self.ctx.workflow_manager['parallelism_instructions']))
        else:
            self.ctx.workflow_manager['parallelism_instructions'] = {}  
        
        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager['true_iter'].pop(), 
                                            wfl_settings = self.ctx.workflow_settings,) 

        self.ctx.final_result = {}     

        self.report('Workflow type: {}; looking for convergence of {}'.format(self.ctx.workflow_settings['type'], self.ctx.workflow_settings['what']))

        
        #self.report('Space of parameters: {}'.format(self.ctx.workflow_manager['parameter_space']))
        
        self.report("Workflow initilization step completed, the parameters will be: {}.".format(self.ctx.calc_manager['var']))

    def has_to_continue(self): #AAAAA check if the space is not large enough.
        
        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.workflow_manager['fully_success']: 
            self.report('Workflow finished')
            return False

        elif not self.ctx.calc_manager['success'] and \
                    self.ctx.calc_manager['iter'] == self.ctx.calc_manager['max_iterations']:
            self.report('Workflow failed due to max restarts exceeded for variable {}'.format(self.ctx.calc_manager['var']))

            return False
        
        elif not self.ctx.calc_manager['success'] and \
                    self.ctx.calc_manager['iter'] > self.ctx.calc_manager['max_iterations']:
            self.report('Workflow failed due to some failed calculation in the investigation of {}'.format(self.ctx.calc_manager['var']))

            return False
        
        elif self.ctx.small_space:
            self.report('space not large enough to complete convergence')
            
            return False

        elif self.ctx.calc_manager['success']:
            #update variable to conv
            if 'converge_b_ratio' in self.ctx.hint.keys():
                self.report('success for this G, now we go on')
                if self.ctx.calc_manager['G_iter'] > self.ctx.calc_manager['global_iterations']:
                    self.report('but no more attempts availables')
                    self.ctx.calc_manager['success']=False
                    return False
                
                return True



            self.ctx.remaining_iter.pop()
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager['true_iter'].pop(), 
                                            wfl_settings = self.ctx.workflow_settings,)

            if self.ctx.calc_manager['convergence_algorithm'] == 'netwon_1D_ratio':
                self.ctx.params_space, self.ctx.workflow_manager['parameter_space'],self.ctx.small_space = create_space(starting_inputs = self.ctx.workflow_manager['parameter_space'],
                                                                        calc_dict = self.ctx.calc_manager,
                                                                        hint=self.ctx.hint,
                                                                        )
                self.ctx.workflow_manager['parameter_space'] = copy.deepcopy(self.ctx.params_space)
            self.report('Next parameters: {}'.format(self.ctx.calc_manager['var']))
            self.ctx.hint = {}
            if self.ctx.workflow_manager['type'] == 'cheap':
                self.report('Mode is "cheap", so we reset the other parameters to the initial ones.')
                self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
            else:
                self.report('Mode is "heavy", so we mantain the other parameters as the converged ones, if any.')
            
            return True
      
        elif not self.ctx.calc_manager['success']:
            self.report('Still iteration on {}'.format(self.ctx.calc_manager['var']))
            
            return True
       
        else:
            self.report('Undefined state on {}, so we exit'.format(self.ctx.calc_manager['var']))
            self.ctx.calc_manager['success'] = 'undefined'
            
            return False


    def next_step(self):
        """This function will submit the next step"""
        self.ctx.calc_manager['iter'] +=1
        self.ctx.calc_manager['skipped'] = 0

        #loop on the given steps of given variables
        calc = {}
        self.ctx.workflow_manager['values'] = []
        if self.ctx.calc_manager['iter'] == 1: self.ctx.params_space = copy.deepcopy(self.ctx.workflow_manager['parameter_space'])
        l = len(self.ctx.params_space[self.ctx.calc_manager['var'][0]])
        for i in range(self.ctx.calc_manager['steps']):

            if 'new_algorithm' in self.ctx.calc_manager['convergence_algorithm'] and i > l-1:
                self.ctx.calc_manager['skipped'] += 1
                continue

            self.ctx.calc_inputs, value, already_done, parent_nscf = updater(self.ctx.calc_manager, 
                                                self.ctx.calc_inputs,
                                                self.ctx.params_space, 
                                                self.ctx.workflow_manager,
                                                i)
                                    
            self.ctx.workflow_manager['values'].append(value)
            self.report('New parameters are: {}'.format(value))
            
            if not already_done:
                self.ctx.calc_inputs.metadata.call_link_label = 'iteration_'+str(self.ctx.workflow_manager['global_step']+i)
                #if parent_nscf and not hasattr(self.ctx.calc_inputs,'parent_folder'):
                    #self.report('Recovering NSCF/P2Y parent: {}'.format(parent_nscf))
                future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
                self.ctx.workflow_manager['group'].add_nodes(future.caller)
            else:
                self.report('Calculation already done: {}'.format(already_done))
                future = load_node(already_done)

            calc[str(i+1)] = future
            self.ctx.workflow_manager['wfl_pk'] = [future.pk] + self.ctx.workflow_manager['wfl_pk']  
            self.ctx.workflow_manager['group'].add_nodes(future) #when added the whole YC, remove that

        return ToContext(calc)


    def data_analysis(self):
        
        self.report('Data analysis, we will try to parse some result and decide what next')
        quantities = take_quantities(self.ctx.calc_manager, self.ctx.workflow_manager)
        self.ctx.final_result = update_story_global(self.ctx.calc_manager, quantities, self.ctx.calc_inputs,\
                         workflow_dict=self.ctx.workflow_manager)
        
        errors = self.ctx.final_result.pop('errors')
        if errors: 
            self.ctx.none_encountered = True
            self.ctx.calc_manager['iter'] = 2*self.ctx.calc_manager['max_iterations']
            return

        self.ctx.calc_manager['success'], oversteps, self.ctx.none_encountered, quantityes, self.ctx.hint = \
                analysis_and_decision(self.ctx.calc_manager, self.ctx.workflow_manager, hints = self.ctx.hint)
        
        self.report('results {}\n:{}'.format(self.ctx.workflow_manager['what'], quantityes))
        self.report('HINTS: {}'.format(self.ctx.hint))

        if self.ctx.calc_manager['success']:

            self.report('Success, updating the history... ')
            self.ctx.final_result = post_analysis_update(self.ctx.calc_inputs,\
                 self.ctx.calc_manager, oversteps, self.ctx.none_encountered, success=True, workflow_dict=self.ctx.workflow_manager)
            
            #self.report(self.ctx.final_result)

            df_story = pd.DataFrame.from_dict(self.ctx.workflow_manager['workflow_story'])
            self.report('Success of '+self.ctx.workflow_settings['type']+' on {} reached in {} calculations, the result is {}' \
                        .format(self.ctx.calc_manager['var'], (self.ctx.calc_manager['steps']-self.ctx.calc_manager['skipped'])*self.ctx.calc_manager['iter'],\
                            df_story[df_story['useful'] == True].loc[:,self.ctx.workflow_manager['what']].values[-1:]))

            if self.ctx.workflow_manager['true_iter'] == [] and not 'converge_b_ratio' in self.ctx.hint.keys(): #variables to be converged are finished
                    self.ctx.workflow_manager['fully_success'] = True
                    return 

            self.report(self.ctx.calc_manager)
            if self.ctx.hint and not 'dummy' in self.ctx.calc_manager['convergence_algorithm']: 
                #self.report('hint: {}'.format(self.ctx.hint))
                self.ctx.extrapolated = self.ctx.hint.pop('extra', None)
                self.ctx.extrapolated = self.ctx.hint.pop('extrapolation', None)
                self.ctx.infos = self.ctx.hint

                if 'converge_b_ratio' in self.ctx.hint.keys(): 
                    self.ctx.calc_manager['iter'] = 0
                    self.ctx.calc_manager['G_iter'] +=1
                    if not 'NGsBlkXp' in self.ctx.hint.keys():
                        self.ctx.hint['NGsBlkXp']=self.ctx.workflow_manager['parameter_space']['NGsBlkXp'][1]
                        #self.report(self.ctx.hint)

                self.ctx.params_space, self.ctx.workflow_manager['parameter_space'],self.ctx.small_space = create_space(starting_inputs = self.ctx.workflow_manager['parameter_space'],
                                                                        calc_dict = self.ctx.calc_manager,
                                                                        hint=self.ctx.hint,
                                                                        )
                
                    
                self.ctx.workflow_manager['parameter_space'] = copy.deepcopy(self.ctx.params_space)

        elif self.ctx.none_encountered:
            self.report('Some calculations failed, updating the history and exiting... ')
            
            self.ctx.final_result = post_analysis_update(self.ctx.calc_inputs,\
                 self.ctx.calc_manager, oversteps, self.ctx.none_encountered,success=False, workflow_dict=self.ctx.workflow_manager)
            self.ctx.calc_manager['iter'] = self.ctx.calc_manager['max_iterations']+1 #exiting the workflow

        else:
            self.report('Success on {} not reached yet in {} calculations' \
                        .format(self.ctx.calc_manager['var'], (self.ctx.calc_manager['steps']-self.ctx.calc_manager['skipped'])*self.ctx.calc_manager['iter']))
            

            if self.ctx.hint: 
                if 'new_grid' in self.ctx.hint.keys():
                    if self.ctx.hint['new_grid']: 
                        self.ctx.final_result = post_analysis_update(self.ctx.calc_inputs,\
                        self.ctx.calc_manager, oversteps, self.ctx.none_encountered,success='new_grid', workflow_dict=self.ctx.workflow_manager)
                #self.report('hint: {}'.format(self.ctx.hint))
                self.ctx.infos = self.ctx.hint
                if 'converge_b_ratio' in self.ctx.hint.keys(): 
                    #self.ctx.calc_manager['iter'] = 0
                    #self.ctx.calc_manager['G_iter'] +=1
                    if not 'NGsBlkXp' in self.ctx.hint.keys():
                        self.ctx.hint['NGsBlkXp']=self.ctx.workflow_manager['parameter_space']['NGsBlkXp'][1]
                        #self.report(self.ctx.hint)

                #self.report('HINT: {}'.format(self.ctx.hint))
                self.ctx.params_space, self.ctx.workflow_manager['parameter_space'],self.ctx.small_space = create_space(starting_inputs = self.ctx.workflow_manager['parameter_space'],
                                                                        calc_dict = self.ctx.calc_manager,
                                                                        hint=self.ctx.hint,
                                                                        )
                
                #self.report('params_space: {}'.format(self.ctx.params_space))
                #self.report('workflow_manager_PS: {}'.format(self.ctx.workflow_manager['parameter_space']))
        #self.report(self.ctx.params_space)

        
        self.ctx.workflow_manager['first_calc'] = False
        
    def report_wf(self):

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager['fully_success'])))
        story = store_Dict(self.ctx.workflow_manager['workflow_story'])
        self.out('history', story)
        #if hasattr(self.ctx,'infos'): 
            #infos = store_Dict(self.ctx.infos)
            #self.out('infos',infos)
        try:
            calc = load_node(self.ctx.final_result['uuid'])
            if self.ctx.workflow_manager['fully_success']: calc.set_extra('converged', True)
            self.out_many(self.exposed_outputs(calc,YamboWorkflow))
        except:
            self.report('no YamboWorkflows available to expose outputs')

        if not self.ctx.calc_manager['success'] and self.ctx.none_encountered:
            remaining_iter = store_List(self.ctx.remaining_iter)
            self.out('remaining_iter', remaining_iter)
            self.report('Some calculation failed, so we stopped the workflow')
            return self.exit_codes.CALCS_FAILED
        elif self.ctx.small_space:
            remaining_iter = store_List(self.ctx.remaining_iter)
            self.out('remaining_iter', remaining_iter)
            self.report('Space too small to complete convergence.')
            return self.exit_codes.SPACE_TOO_SMALL    
        elif not self.ctx.calc_manager['success']:
            remaining_iter = store_List(self.ctx.remaining_iter)
            self.out('remaining_iter', remaining_iter)
            self.report('Convergence not reached')
            return self.exit_codes.CONVERGENCE_NOT_REACHED
        elif self.ctx.calc_manager['success'] == 'undefined':
            remaining_iter = store_List(self.ctx.remaining_iter)
            self.out('remaining_iter', remaining_iter)
            self.report('Undefined state')
            return self.exit_codes.UNDEFINED_STATE    


############################### preliminary calculation #####################
    def pre_needed(self):

        if 'skip_pre' in self.ctx.workflow_settings.keys():
            if  self.ctx.workflow_settings['skip_pre']: 
                self.report('skipping pre, debug mode')
                return False
        
        if not hasattr(self.ctx,'params_space'):
            self.ctx.params_space = copy.deepcopy(self.ctx.workflow_manager['parameter_space'])
        #self.report('detecting if we need a starting calculation...')
        self.report(self.ctx.workflow_manager['parameter_space'])        
        
        if self.ctx.how_bands == 'all-at-once' or  isinstance(self.ctx.how_bands, int) or 'new_alg' in self.ctx.calc_manager['convergence_algorithm']:
            self.ctx.space_index = 0
            #if 'BndsRnXp' in self.ctx.workflow_manager['parameter_space'].keys() and len(self.ctx.params_space['BndsRnXp'])>0: 
                #self.report('Max #bands needed in the whole convergence = {}'.format(max(self.ctx.params_space['BndsRnXp'])))
                
        elif self.ctx.how_bands == 'single-step' and 'BndsRnXp' in self.ctx.calc_manager['var']:
            self.ctx.space_index = self.ctx.calc_manager['steps']*(1+self.ctx.calc_manager['iter'])
            if self.ctx.space_index  >= len(self.ctx.params_space['BndsRnXp']): self.ctx.space_index = 0
            #self.report('Max #bands needed in this step = {}'.format(max(self.ctx.params_space['BndsRnXp'][:self.ctx.space_index-1])))
        elif self.ctx.how_bands == 'single-step' and 'GbndRnge' in self.ctx.calc_manager['var']:
            self.ctx.space_index = self.ctx.calc_manager['steps']*(1+self.ctx.calc_manager['iter'])
            if self.ctx.space_index  >= len(self.ctx.params_space['BndsRnXp']): self.ctx.space_index = 0
            #self.report('Max #bands needed in this step = {}'.format(max(self.ctx.params_space['BndsRnXp'][:self.ctx.space_index-1])))
        elif self.ctx.how_bands == 'full-step' and 'BndsRnXp' in self.ctx.calc_manager['var']:
            #self.report(self.ctx.params_space['BndsRnXp'])
            self.ctx.space_index = self.ctx.calc_manager['steps']*self.ctx.calc_manager['max_iterations']
            if self.ctx.space_index  >= len(self.ctx.params_space['BndsRnXp']): self.ctx.space_index = 0
            #self.report('Max #bands needed in this iteration = {}'.format(max(self.ctx.params_space['BndsRnXp'][:self.ctx.space_index-1])))
        elif self.ctx.how_bands == 'full-step' and 'GbndRnge' in self.ctx.calc_manager['var']:
            self.ctx.space_index = self.ctx.calc_manager['steps']*self.ctx.calc_manager['max_iterations']
            if self.ctx.space_index  >= len(self.ctx.params_space['BndsRnXp']): self.ctx.space_index = 0
            #self.report('Max #bands needed in this iteration = {}'.format(max(self.ctx.params_space['BndsRnXp'][:self.ctx.space_index-1])))
        
        if 'BndsRnXp' in self.ctx.workflow_manager['parameter_space'].keys() and 'BndsRnXp' in self.ctx.calc_manager['var']:
            yambo_bandsX = max(self.ctx.workflow_manager['parameter_space']['BndsRnXp'][:self.ctx.space_index-1])
        else:
            yambo_bandsX = 0 
        if 'GbndRnge' in self.ctx.workflow_manager['parameter_space'].keys() and 'GbndRnge' in self.ctx.calc_manager['var']:
            yambo_bandsSc = max(self.ctx.workflow_manager['parameter_space']['GbndRnge'][:self.ctx.space_index-1])
        else:
            yambo_bandsSc = 0

        self.ctx.gwbands = max(yambo_bandsX,yambo_bandsSc)
        if 'BndsRnXp' in self.ctx.calc_manager['var'] or 'GbndRnge' in self.ctx.calc_manager['var']:
            if self.ctx.gwbands > 0 and isinstance(self.ctx.how_bands, int):
                self.ctx.gwbands = min(self.ctx.gwbands, self.ctx.how_bands)


        if 'kpoint_mesh' in self.ctx.calc_manager['var'] or 'kpoint_density' in self.ctx.calc_manager['var']:
            #self.report('Not needed, we start with k-points')
            return False

        try:
            already_done, parent_nscf, parent_scf = search_in_group(self.ctx.calc_inputs, 
                                                self.ctx.workflow_manager['group'], up_to_p2y = True,)

            #self.report(already_done,)
            #self.report(parent_nscf)
            #self.report(parent_scf)

            if already_done:
                try:
                    self.ctx.calc_inputs.parent_folder =  load_node(already_done).outputs.remote_folder 
                except:
                    pass
            elif parent_nscf:
                try:
                    self.ctx.calc_inputs.parent_folder =  load_node(parent_nscf).outputs.remote_folder 
                except:
                    pass
            elif parent_scf:
                try:
                    self.ctx.calc_inputs.parent_folder =  load_node(parent_scf).outputs.remote_folder 
                except:
                    pass

            scf_params, nscf_params, redo_nscf, self.ctx.bands, messages = quantumespresso_input_validator(self.ctx.calc_inputs)
            self.report(messages)
            self.ctx.gwbands = max(self.ctx.gwbands,self.ctx.bands)
            parent_calc = take_calc_from_remote(self.ctx.calc_inputs.parent_folder) 
            
            nbnd = nscf_params.get_dict()['SYSTEM']['nbnd']

            if nbnd < self.ctx.gwbands:
                #self.report('we have to compute the nscf part: not enough bands, we need {} bands to complete all the calculations'.format(self.ctx.gwbands))
                set_parent(self.ctx.calc_inputs, find_pw_parent(parent_calc, calc_type = ['scf']))
                return True
            elif parent_calc.process_type=='aiida.calculations:yambo.yambo' and not hasattr(self.inputs, 'precalc_inputs'):
                #self.report('not required, yambo parent and no precalc requested')   
                return False         
            elif hasattr(self.inputs, 'precalc_inputs'):
                #self.report('yes, precalc requested in the inputs')
                return True
            else:
                #self.report('yes, no yambo parent')
                return True
        except:
            try:
                already_done, parent_nscf, parent_scf = search_in_group(self.ctx.calc_inputs, 
                                            self.ctx.workflow_manager['group'], up_to_p2y = True)
            
                if already_done: 
                    set_parent(self.ctx.calc_inputs, load_node(already_done))
                    #self.report('yambo parent found in group: p2y not needed')
                    return False
                
                elif parent_nscf: 
                    set_parent(self.ctx.calc_inputs, load_node(parent_nscf))
                    #self.report('yes, no yambo parent, setting parent nscf found in group')
                    return True
                
                else: 
                    parent_calc = take_calc_from_remote(self.ctx.calc_inputs.parent_folder)              
                    set_parent(self.ctx.calc_inputs, find_pw_parent(parent_calc, calc_type = ['scf']))
                    #self.report('yes, no yambo parent, setting parent scf')
                    return True
            except:
                #self.report('no available parent folder, so we start from scratch')
                return True

    def do_pre(self):
        self.ctx.pre_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.pre_inputs.yres.clean_workdir = Bool(False)

        if hasattr(self.ctx.calc_inputs, 'parent_folder'):
            set_parent(self.ctx.pre_inputs, self.ctx.calc_inputs.parent_folder)
        
        if hasattr(self.ctx.calc_inputs.nscf,'kpoints'):
            self.report('mesh check')
            self.ctx.pre_inputs.nscf.kpoints = self.ctx.calc_inputs.nscf.kpoints

        if hasattr(self.inputs, 'precalc_inputs'):
            self.ctx.calculation_type='pre_yambo'
            self.ctx.pre_inputs.yres.yambo.parameters = self.inputs.precalc_inputs
            self.ctx.pre_inputs.additional_parsing = self.ctx.calc_inputs.additional_parsing 
        else:
            self.ctx.calculation_type='p2y'
            self.ctx.pre_inputs.yres.yambo.parameters = update_dict(self.ctx.pre_inputs.yres.yambo.parameters, 
                                                            ['GbndRnge','BndsRnXp'], [[[1,self.ctx.gwbands],''],[[1,self.ctx.gwbands],'']],sublevel='variables')
            #self.report(self.ctx.pre_inputs.yres.yambo.parameters.get_dict())
            self.ctx.pre_inputs.yres.yambo.settings = update_dict(self.ctx.pre_inputs.yres.yambo.settings, 'INITIALISE', True)
            if hasattr(self.ctx.pre_inputs, 'additional_parsing'):
                delattr(self.ctx.pre_inputs, 'additional_parsing')

        self.report('doing the calculation: {}'.format(self.ctx.calculation_type))
        calc = {}
        self.ctx.pre_inputs.metadata.call_link_label = self.ctx.calculation_type
        calc[self.ctx.calculation_type] = self.submit(YamboWorkflow, **self.ctx.pre_inputs) #################run
        self.ctx.PRE = calc[self.ctx.calculation_type]
        self.report('Submitted YamboWorkflow up to {}, pk = {}'.format(self.ctx.calculation_type,calc[self.ctx.calculation_type].pk))
        self.ctx.workflow_manager['group'].add_nodes(calc[self.ctx.calculation_type]) #when added the whole YC, remove that

        load_node(calc[self.ctx.calculation_type].pk).label = self.ctx.calculation_type

        if hasattr(self.inputs, 'precalc_inputs'):
            self.ctx.calc_inputs.yres.yambo.settings = update_dict(self.ctx.calc_inputs.yres.yambo.settings, 'COPY_DBS', True)
        else:
            self.ctx.calc_inputs.yres.yambo.settings = update_dict(self.ctx.calc_inputs.yres.yambo.settings, 'INITIALISE', False)

        return ToContext(calc)

    def prepare_calculations(self):
        if not self.ctx.PRE.is_finished_ok:
            self.report('the pre calc was not succesful, exiting...')
            return self.exit_codes.PRECALC_FAILED

        self.report('setting the pre calc remote folder {} as parent'.format(self.ctx.PRE.outputs.remote_folder.pk))
        set_parent(self.ctx.calc_inputs, self.ctx.PRE.outputs.remote_folder)


if __name__ == "__main__":
    pass
