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
                            exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

        spec.expose_inputs(YamboWorkflow, namespace='p2y', namespace_options={'required': True}, \
                            exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

        spec.expose_inputs(YamboWorkflow, namespace='precalc', namespace_options={'required': False}, \
                    exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

        spec.input('kpoints', valid_type=KpointsData, required = True)
        spec.input('parent_folder', valid_type=RemoteData, required = False)

        spec.input("parameters_space", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max iterations')
        spec.input("workflow_settings", valid_type=Dict, required=True, \
                    help = 'settings for the workflow: type, quantity to be examinated...')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    if_(cls.p2y_needed)(
                    cls.do_p2y,
                    cls.prepare_calculations,
                    ),
                    if_(cls.precalc_needed)(
                    cls.do_precalc,
                    cls.post_processing,
                    ),
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

        spec.exit_code(300, 'UNDEFINED_STATE',
                             message='The workchain is in an undefined state.')
        spec.exit_code(301, 'P2Y_FAILED',
                             message='The workchain failed the p2y step.')  
        spec.exit_code(302, 'PRECALC_FAILED',
                             message='The workchain failed the precalc step.')                                      
        spec.exit_code(400, 'CONVERGENCE_NOT_REACHED',
                             message='The workchain failed to reach convergence.')

    def start_workflow(self):
        """Initialize the workflow"""

        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints, self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints, self.inputs.kpoints

        self.ctx.p2y_inputs = self.exposed_inputs(YamboWorkflow, 'p2y')
        self.ctx.p2y_inputs.scf.kpoints, self.ctx.p2y_inputs.nscf.kpoints = self.ctx.calc_inputs.scf.kpoints, self.ctx.calc_inputs.nscf.kpoints

        self.ctx.precalc_inputs = self.exposed_inputs(YamboWorkflow, 'precalc')
        self.ctx.precalc_inputs.scf.kpoints, self.ctx.precalc_inputs.nscf.kpoints = self.ctx.calc_inputs.scf.kpoints, self.ctx.calc_inputs.nscf.kpoints
        
        self.ctx.workflow_manager = convergence_workflow_manager(self.inputs.parameters_space, self.inputs.workflow_settings.get_dict())

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop(), wfl_settings = self.inputs.workflow_settings.get_dict()) 

        self.ctx.final_result = []      

        self.report('Workflow on {}'.format(self.inputs.workflow_settings.get_dict()['type']))
        self.report("workflow initilization step completed, the parameters will be: {}.".format(self.ctx.calc_manager.var))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.workflow_manager.fully_success:
            self.report('Workflow finished')
            return False

        elif not self.ctx.calc_manager.success and \
                    self.ctx.calc_manager.iter >= self.ctx.calc_manager.max_iterations:
            self.report('Workflow failed due to max restarts exceeded for variable {}'.format(self.ctx.calc_manager.var))

            return False

        elif self.ctx.calc_manager.success:
            #update variable to conv
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop(), wfl_settings = self.inputs.workflow_settings.get_dict())
            self.report('Next parameters: {}'.format(self.ctx.calc_manager.var))
            
            return True
      
        elif not self.ctx.calc_manager.success:
            self.report('Still iteration on {}'.format(self.ctx.calc_manager.var))
            
            return True
       
        else:
            self.report('Undefined state on {}, so we exit'.format(self.ctx.calc_manager.var))
            self.ctx.calc_manager.success = 'undefined'
            
            return False


    def next_step(self):
        """This function will submit the next step"""
        self.ctx.calc_manager.iter +=1
        
        #loop on the given steps of given variables
        calc = {}
        self.ctx.workflow_manager.values = []
        parameters_space = self.ctx.calc_manager.parameters_space_creator(self.ctx.workflow_manager.first_calc, \
                            take_calc_from_remote(self.ctx.calc_inputs.parent_folder), \
                            self.ctx.calc_inputs.yres.yambo.parameters.get_dict())
        self.report('parameter space will be {}'.format(parameters_space))
        self.ctx.calc_manager.steps = len(parameters_space)
        for parameter in parameters_space:
            self.report(parameter)
            self.ctx.calc_inputs, value = \
                        self.ctx.calc_manager.updater(self.ctx.calc_inputs, parameter)

            self.ctx.workflow_manager.values.append(value)
            self.report('Preparing iteration number {} on {}: {}'.format((self.ctx.calc_manager.iter-1)* \
                        self.ctx.calc_manager.steps \
                        + parameters_space.index(parameter)+1,parameter[0],value))

            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(parameters_space.index(parameter))] = future
            self.ctx.calc_manager.wfl_pk = future.pk


        return ToContext(calc)


    def data_analysis(self):

        self.report('Data analysis, we will try to parse some result and decide what next')
        post_processor = the_evaluator(self.ctx.calc_manager) 

        quantities = self.ctx.calc_manager.take_quantities()
        self.ctx.workflow_manager.build_story_global(self.ctx.calc_manager, quantities)
        
        self.report('results: {}'.format(self.ctx.workflow_manager.array_conv))
        
        self.ctx.calc_manager.success, oversteps = \
                post_processor.analysis_and_decision(self.ctx.workflow_manager.array_conv)

        self.ctx.workflow_manager.update_story_global(self.ctx.calc_manager, quantities, self.ctx.calc_inputs)

        #self.report('The history:')
        #self.report(self.ctx.workflow_manager.workflow_story)

        if self.ctx.calc_manager.success:

            self.report('Success, updating the history... ')
            self.ctx.final_result = self.ctx.workflow_manager.post_analysis_update(self.ctx.calc_inputs, self.ctx.calc_manager, oversteps)
            
            self.report('Success of '+self.inputs.workflow_settings.get_dict()['type']+' on {} reached in {} calculations, the result is {}' \
                        .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter,\
                            self.ctx.workflow_manager.workflow_story[self.ctx.workflow_manager.workflow_story.useful == True].iloc[-1]['result_eV']))

            if self.ctx.workflow_manager.true_iter == [] : #variables to be converged are finished
                    self.ctx.workflow_manager.fully_success = True

        else:
            self.report('Success on {} not reached yet in {} calculations' \
                        .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter))

        self.ctx.workflow_manager.first_calc = False

    def report_wf(self):

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager.fully_success)))
        
        story = store_Dict(self.ctx.workflow_manager.workflow_story.to_dict())
        self.out('history', story)
        final_result = store_Dict(self.ctx.final_result)
        self.out('last_calculation',final_result)


        if not self.ctx.calc_manager.success:
            self.report('Convergence not reached')
            return self.exit_codes.CONVERGENCE_NOT_REACHED
        elif self.ctx.calc_manager.success == 'undefined':
            self.report('Undefined state')
            return self.exit_codes.UNDEFINED_STATE

        remote_folder = load_node(final_result['calculation_uuid']).outputs.remote_folder
        self.out('last_calculation_remote_folder',remote_folder)

###############################starting p2y#####################
    def p2y_needed(self):
        self.report('do we need a p2y??')

        self.report('detecting if we need a p2y starting calculation...')

        try:
            set_parent(self.ctx.p2y_inputs, self.inputs.parent_folder)
            set_parent(self.ctx.precalc_inputs, self.inputs.parent_folder)
            set_parent(self.ctx.calc_inputs, self.inputs.parent_folder)
            parent_calc = take_calc_from_remote(self.ctx.p2y_inputs.parent_folder)
            if parent_calc.process_type=='aiida.calculations:yambo.yambo':
                self.report('no, yambo parent')
                return False
            else:
                self.report('yes, no yambo parent')
                return True
        except:
            self.report('no available parent folder, so we start from scratch')
            return True

    def do_p2y(self):
        self.report('doing the p2y')
        calc = {}
        self.report('no valid parent folder, so we will create it')
        self.ctx.p2y_inputs.yres.yambo.settings = update_dict(self.ctx.p2y_inputs.yres.yambo.settings, 'INITIALISE', True)
        calc['p2y'] = self.submit(YamboWorkflow, **self.ctx.p2y_inputs) #################run
        self.report('Submitted YamboWorkflow up to p2y, pk = {}'.format(calc['p2y'].pk))
        self.ctx.p2y_inputs.yres.yambo.settings = update_dict(self.ctx.p2y_inputs.yres.yambo.settings, 'INITIALISE', False)
        self.ctx.p2y = calc['p2y']
        self.report('setting label "p2y _on YC"')
        load_node(calc['p2y'].pk).label = 'p2y _on YC'

        return ToContext(calc)

    def prepare_calculations(self):
        if not self.ctx.p2y.is_finished_ok:
            self.report('the p2y calc was not succesful, exiting...')
            return self.exit_codes.P2Y_FAILED

        self.report('setting the p2y calc as parent')
        set_parent(self.ctx.calc_inputs, self.ctx.p2y.outputs.remote_folder)

############################### starting precalculation ####################


    def precalc_needed(self):
        self.report('do we need a preliminary calculation ??')
        self.report('detecting if we need a preliminary calculation...')
        needed = self.inputs.workflow_settings.get_dict().pop('PRE_CALC')
        self.report(needed)
        if needed:
            return True
        else:
            return False


    def do_precalc(self):
        self.report('doing the preliminary calculation')
        calc = {}
        self.ctx.precalc_inputs = self.exposed_inputs(YamboWorkflow, 'precalc')
        set_parent(self.ctx.precalc_inputs, self.ctx.calc_inputs.parent_folder)
        calc['PRE_CALC'] = self.submit(YamboWorkflow, **self.ctx.precalc_inputs) #################run
        self.report('Submitted preliminary YamboWorkflow, pk = {}'.format(calc['PRE_CALC'].pk))
        self.ctx.PRE = calc['PRE_CALC']
        self.report('setting label "precalc _on YC"')
        load_node(calc['PRE_CALC'].pk).label = 'precalc _on YC'

        return ToContext(calc)

    def post_processing(self):
        if not self.ctx.PRE.is_finished_ok:
            self.report('the precalc was not succesful, exiting...')
            return self.exit_codes.PRECALC_FAILED
        
        self.report('setting the preliminary calc as parent and its db as starting one')
        set_parent(self.ctx.calc_inputs, self.ctx.PRE.outputs.remote_folder)

        self.ctx.calc_inputs.yres.yambo.settings = update_dict(self.ctx.calc_inputs.yres.yambo.settings, 'COPY_DBS', True)



if __name__ == "__main__":
    pass
