# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

#if aiida_calcs:
from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_ , if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.helpers_aiida_yambo import *
from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
from aiida_yambo.workflows.utils.helpers_workflow import *
from aiida_yambo.utils.common_helpers import *

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences with respect to some parameter. It can be used also to run multi-parameter
       calculations.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl', namespace_options={'required': True}, \
                            exclude = ('kpoints','parent_folder'))
        
        spec.input('kpoints', valid_type=KpointsData, required = True)
        spec.input('parent_folder', valid_type=RemoteData, required = False)

        spec.input('precalc_inputs', valid_type=Dict, required = False)

        spec.input("parameters_space", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max iterations')
        spec.input("workflow_settings", valid_type=Dict, required=True, \
                    help = 'settings for the workflow: type, quantity to be examinated...')
        spec.input("parallelism_instructions", valid_type=Dict, required=False, \
                    help = 'indications for the parallelism to be used wrt values of the parameters.')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    if_(cls.pre_needed)(
                    cls.do_pre,
                    cls.prepare_calculations),
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.data_analysis),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('history', valid_type = Dict, help='all calculations')
        spec.output('last_calculation', valid_type = Dict, help='final useful calculation')
        spec.output('last_calculation_remote_folder', valid_type = RemoteData, required = False, \
                                                      help='final remote folder')
        spec.output('remaining_iter', valid_type = List,  required = False, help='remaining convergence iter')       

        spec.exit_code(300, 'UNDEFINED_STATE',
                             message='The workchain is in an undefined state.') 
        spec.exit_code(301, 'PRECALC_FAILED',
                             message='The workchain failed the precalc step.')    
        spec.exit_code(302, 'CALCS_FAILED',
                             message='The workchain failed some calculations.')                                 
        spec.exit_code(400, 'CONVERGENCE_NOT_REACHED',
                             message='The workchain failed to reach convergence.')

    def start_workflow(self):
        """Initialize the workflow"""

        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.kpoints = self.inputs.kpoints
        
        self.ctx.remaining_iter = self.inputs.parameters_space.get_list()
        self.ctx.remaining_iter.reverse()

        self.ctx.workflow_manager = convergence_workflow_manager(self.inputs.parameters_space,
                                                                self.inputs.workflow_settings.get_dict()  ,
                                                                self.ctx.calc_inputs.yres.yambo.parameters.get_dict(), 
                                                                self.inputs.kpoints,
                                                                )

        if 'BndsRnXp' in self.ctx.workflow_manager['parameter_space'].keys():
            yambo_bandsX = self.ctx.workflow_manager['parameter_space']['BndsRnXp'][-1][-1]
        else:
            yambo_bandsX = 0 
        if 'GbndRnge' in self.ctx.workflow_manager['parameter_space'].keys():
            yambo_bandsSc = self.ctx.workflow_manager['parameter_space']['GbndRnge'][-1][-1]
        else:
            yambo_bandsSc = 0

        self.ctx.bands = max(yambo_bandsX,yambo_bandsSc)

        if hasattr(self.inputs, "parallelism_instructions"):
            self.ctx.workflow_manager['parallelism_instructions'] = build_parallelism_instructions(self.inputs.parallelism_instructions.get_dict(),)
        else:
            self.ctx.workflow_manager['parallelism_instructions'] = {}  

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager['true_iter'].pop(), 
                                            wfl_settings = self.inputs.workflow_settings.get_dict(),) 

        self.ctx.final_result = {}     

        self.report('Workflow on {}'.format(self.inputs.workflow_settings.get_dict()['type']))
        
        self.report('Space of parameters: {}'.format(self.ctx.workflow_manager['parameter_space']))
        
        self.report("Workflow initilization step completed, the parameters will be: {}.".format(self.ctx.calc_manager['var']))

    def has_to_continue(self):
        
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

        elif self.ctx.calc_manager['success']:
            #update variable to conv
            self.ctx.remaining_iter.pop()
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager['true_iter'].pop(), 
                                            wfl_settings = self.inputs.workflow_settings.get_dict(),)

            self.report('Next parameters: {}'.format(self.ctx.calc_manager['var']))
            
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
        
        #loop on the given steps of given variables
        calc = {}
        self.ctx.workflow_manager['values'] = []
        for i in range(self.ctx.calc_manager['steps']):
            #self.report(parameter)
            self.ctx.calc_inputs, value = updater(self.ctx.calc_manager, 
                                                self.ctx.calc_inputs, 
                                                self.ctx.workflow_manager['parameter_space'], 
                                                self.ctx.workflow_manager['parallelism_instructions'])
            self.ctx.workflow_manager['values'].append(value)
            self.report('New parameters are: {}'.format(value))
            self.report('Preparing iteration number {} on: {}'.format((self.ctx.calc_manager['iter']-1)*self.ctx.calc_manager['steps']+i+1,
                        value))

            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i+1)] = future
            self.ctx.calc_manager['wfl_pk'] = future.pk

        return ToContext(calc)


    def data_analysis(self):

        self.report('Data analysis, we will try to parse some result and decide what next')
        post_processor = the_evaluator(self.ctx.calc_manager) 

        quantities = take_quantities(self.ctx.calc_manager)

        build_story_global(self.ctx.calc_manager, quantities, workflow_dict=self.ctx.workflow_manager)
        
        self.report('results: {}'.format(np.array(self.ctx.workflow_manager['array_conv'])))
        
        self.ctx.calc_manager['success'], oversteps, self.ctx.none_encountered = \
                post_processor.analysis_and_decision(self.ctx.workflow_manager['array_conv'])

        self.ctx.final_result = update_story_global(self.ctx.calc_manager, quantities, self.ctx.calc_inputs,\
                         workflow_dict=self.ctx.workflow_manager)

        #self.report('The history:')
        #self.report(self.ctx.workflow_manager['workflow_story'])

        if self.ctx.calc_manager['success']:

            self.report('Success, updating the history... ')
            self.ctx.final_result = post_analysis_update(self.ctx.calc_inputs,\
                 self.ctx.calc_manager, oversteps, self.ctx.none_encountered, workflow_dict=self.ctx.workflow_manager)

            df_story = pd.DataFrame.from_dict(self.ctx.workflow_manager['workflow_story'])
            self.report('Success of '+self.inputs.workflow_settings.get_dict()['type']+' on {} reached in {} calculations, the result is {}' \
                        .format(self.ctx.calc_manager['var'], self.ctx.calc_manager['steps']*self.ctx.calc_manager['iter'],\
                            df_story[df_story['useful'] == True].iloc[-1]['result_eV']))

            if self.ctx.workflow_manager['true_iter'] == [] : #variables to be converged are finished
                    self.ctx.workflow_manager['fully_success'] = True
        
        elif self.ctx.none_encountered:
            self.report('Some calculations failed, updating the history and exiting... ')
            
            self.ctx.final_result = post_analysis_update(self.ctx.calc_inputs,\
                 self.ctx.calc_manager, oversteps, self.ctx.none_encountered, workflow_dict=self.ctx.workflow_manager)
            self.ctx.calc_manager['iter'] = self.ctx.calc_manager['max_iterations']+1 #exiting the workflow

        else:
            self.report('Success on {} not reached yet in {} calculations' \
                        .format(self.ctx.calc_manager['var'], self.ctx.calc_manager['steps']*self.ctx.calc_manager['iter']))
                        
        self.ctx.workflow_manager['first_calc'] = False

    def report_wf(self):

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager['fully_success'])))
        
        story = store_Dict(self.ctx.workflow_manager['workflow_story'])
        self.out('history', story)
        final_result = store_Dict(self.ctx.final_result)
        self.out('last_calculation',final_result)

        try:
            remote_folder = load_node(final_result['calculation_uuid']).outputs.remote_folder
            self.out('last_calculation_remote_folder',remote_folder)
        except:
            pass

        if not self.ctx.calc_manager['success'] and self.ctx.none_encountered:
            remaining_iter = store_List(self.ctx.remaining_iter)
            self.out('remaining_iter', remaining_iter)
            self.report('Some calculation failed, so we stopped the workflow')
            return self.exit_codes.CALCS_FAILED
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

        self.report('detecting if we need a starting calculation...')
        
        if 'kpoint' in self.ctx.calc_manager['var']:
            self.report('Not needed, we start with k-points')
            return False
        
        if hasattr(self.inputs, 'precalc_inputs'):
            self.report('Yes, we will do a preliminary calculation')

        try:
            set_parent(self.ctx.calc_inputs, self.inputs.parent_folder)
            parent_calc = take_calc_from_remote(self.ctx.calc_inputs.parent_folder)
            nbnd = find_pw_parent(parent_calc, calc_type = ['nscf']).inputs.parameters.get_dict()['SYSTEM']['nbnd']
            if nbnd < self.ctx.bands:
                self.report('yes, no yambo parent, we have also to recompute the nscf part: not enough bands, we need {} bands to complete all the calculations'.format(self.ctx.bands))
                set_parent(self.ctx.calc_inputs, find_pw_parent(parent_calc, calc_type = ['scf']))
                return True
            elif parent_calc.process_type=='aiida.calculations:yambo.yambo':
                self.report('not required, yambo parent')            
            else:
                self.report('yes, no yambo parent')
                return True
        except:
            try:
                set_parent(self.ctx.calc_inputs, find_pw_parent(parent_calc, calc_type = ['scf']))
                self.report('yes, no yambo parent, setting parent scf')
                return True
            except:
                self.report('no available parent folder, so we start from scratch')
                return True

    def do_pre(self):
        self.ctx.pre_inputs = self.ctx.calc_inputs
        self.ctx.old_inputs = self.ctx.calc_inputs
        if hasattr(self.inputs, 'precalc_inputs'):
            self.ctx.calculation_type='pre_yambo'
            self.ctx.pre_inputs.yres.yambo.parameters = self.precalc_inputs
        else:
            self.ctx.calculation_type='p2y'
            self.ctx.pre_inputs.yres.yambo.parameters = update_dict(self.ctx.pre_inputs.yres.yambo.parameters, ['GbndRnge','BndsRnXp'], [[1,self.ctx.bands],[1,self.ctx.bands]])
            #self.report(self.ctx.pre_inputs.yres.yambo.parameters.get_dict())
            self.ctx.pre_inputs.yres.yambo.settings = update_dict(self.ctx.pre_inputs.yres.yambo.settings, 'INITIALISE', True)

        self.report('doing the calculation: {}'.format(self.ctx.calculation_type))
        calc = {}
        calc[self.ctx.calculation_type] = self.submit(YamboWorkflow, **self.ctx.pre_inputs) #################run
        self.ctx.PRE = calc[self.ctx.calculation_type]
        self.report('Submitted YamboWorkflow up to p2y, pk = {}'.format(calc[self.ctx.calculation_type].pk))

        self.ctx.calc_inputs = self.ctx.old_inputs

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

        self.report('setting the pre calc as parent')
        set_parent(self.ctx.calc_inputs, self.ctx.PRE.outputs.remote_folder)


if __name__ == "__main__":
    pass
