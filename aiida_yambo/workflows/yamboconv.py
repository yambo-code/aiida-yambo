# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

'''
if ypy:
    import _to_context as ctx....
    import wait_calcs as ToContext
    import yambochain as WorkChain ---> with ctx and report....
    import print as report
    from helpers_workflows import *
    list as List...
'''

#if aiida_calcs:
from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_ , if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.helpers_aiida_yambo import calc_manager_aiida_yambo as calc_manager
from aiida_yambo.workflows.utils.helpers_workflow import *

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences with the respect to the gap at gamma... In future for multiple k points.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl', namespace_options={'required': True}, \
                            exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

        spec.input('kpoints', valid_type=KpointsData, required = True) #not from exposed because otherwise I cannot modify it!
        spec.input('parent_folder', valid_type=RemoteData, required = False)

        spec.input("parameters_space", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max restarts')
        spec.input("wfl_type", valid_type=Str, required=True, \
                    help = '1D_convergence, 2D_convergence, 2D_extrapolation...') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    if_(cls.p2y_needed)(
                    cls.do_p2y,
                    cls.prepare_calculations,
                    ),
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.data_analysis),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('story', valid_type = List, help='all calculations')


    def start_workflow(self):
        """Initialize the workflow"""

        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints = self.inputs.kpoints
        self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints

        self.ctx.workflow_manager = workflow_manager(self.inputs.parameters_space, self.inputs.wfl_type)
        self.ctx.workflow_manager.global_step = 0
        self.ctx.workflow_manager.fully_success = False

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop(), wfl_type = self.inputs.wfl_type)
        self.ctx.calc_manager._type = 'yambo'
        self.ctx.calc_manager.iter  = 1
        self.ctx.calc_manager.success = False

        try: #--> need find mesh here
            self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
        except:
            self.ctx.k_distance = 1

        self.ctx.workflow_manager.first_calc = True

        self.report('Workflow on {}'.format(self.ctx.calc_manager.wfl_type.value))
        self.report("workflow initilization step completed, the parameters will be: {}.".format(self.ctx.calc_manager.var))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.workflow_manager.fully_success:
            self.report('Workflow finished')
            return False

        elif not self.ctx.calc_manager.success and \
                    self.ctx.calc_manager.iter > self.ctx.calc_manager.max_restarts +1:
            self.report('Workflow failed due to max restarts exceeded for variable {}'.format(self.ctx.calc_manager.var))
            return False

        elif self.ctx.calc_manager.success:
            #update variable to conv
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop(),  wfl_type = self.inputs.wfl_type)
            self.ctx.calc_manager.type = 'yambo.yambo'
            try:
                self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
            except:
                pass

            self.ctx.calc_manager.iter = 1
            self.ctx.calc_manager.success = False
            self.report('Next parameters: {}'.format(self.ctx.calc_manager.var))
            return True
        elif not self.ctx.calc_manager.success:
            self.report('Still iteration on {}'.format(self.ctx.calc_manager.var))
            return True
        else:
            self.report('Undefined state on {}'.format(self.ctx.calc_manager.var))
            return False


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of given variables
        calc = {}
        self.ctx.workflow_manager.values = []
        parameters_space = self.ctx.calc_manager.parameters_space_creator(self.ctx.workflow_manager.first_calc, \
                            self.ctx.calc_inputs.yres.gw.parameters.get_dict(), \
                            self.ctx.k_distance)
        self.report('parameter space will be {}'.format(parameters_space))
        self.ctx.calc_manager.steps = len(parameters_space)
        for parameter in parameters_space:
            self.report(parameter)
            self.ctx.calc_inputs, value = \
                        self.ctx.calc_manager.updater(self.ctx.calc_inputs, parameter)

            if self.ctx.calc_manager.var == 'kpoints':
                self.ctx.k_distance = value

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
        post_processor = the_evaluator(self.ctx.calc_manager) #.wfl_type, \
                                #self.ctx.calc_manager.conv_window, self.ctx.calc_manager.conv_thr)

        try:
            quantities = self.ctx.calc_manager.take_quantities()
            self.ctx.workflow_manager.build_story_global(self.ctx.calc_manager, quantities)
            self.report('results: {}'.format(self.ctx.workflow_manager.array_conv))
            self.ctx.calc_manager.success, oversteps = \
                    post_processor.analysis_and_decision(self.ctx.workflow_manager.array_conv)

            self.ctx.workflow_manager.update_story_global(self.ctx.calc_manager, quantities)

            if self.ctx.calc_manager.success:
                self.report('Success, updating the history... ')
                self.ctx.workflow_manager.post_analysis_update(self.ctx.calc_inputs, self.ctx.calc_manager, oversteps)
                self.report('Success of '+self.inputs.wfl_type.value+' on {} reached in {} calculations, the gap is {}' \
                            .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter,\
                             self.ctx.workflow_manager.workflow_story[-(oversteps+1)][-2] ))

                if self.ctx.workflow_manager.true_iter == [] : #variables to be converged are finished
                     self.ctx.workflow_manager.fully_success = True

            else:
                self.report('Success on {} not reached yet in {} calculations' \
                            .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter))

        except:
            self.report('problems during the data parsing/analysis, the workflows will stop and collect the previous info, so you can restart from there')
            self.report('the error was: {}'.format(str(traceback.format_exc()))) #debug

        self.ctx.calc_manager.iter +=1
        self.ctx.workflow_manager.first_calc = False
    def report_wf(self):

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager.fully_success)))
        all_var = List(list=self.ctx.workflow_manager.workflow_story).store()
        self.out('story', all_var)

    def p2y_needed(self):
        self.report('do we need a p2y??')

        self.report('detecting if we need a p2y starting calculation...')
        try:
            self.ctx.calc_manager.set_parent(self.ctx.calc_inputs, self.inputs.parent_folder)
            parent_calc = self.ctx.calc_inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
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
        self.ctx.calc_manager.update_dict(self.ctx.calc_inputs.yres.gw.settings, 'INITIALISE', True)
        calc['p2y'] = self.submit(YamboWorkflow, **self.ctx.calc_inputs) #################run
        self.report('Submitted YamboWorkflow up to p2y, pk = {}'.format(calc['p2y'].pk))
        self.ctx.calc_manager.update_dict(self.ctx.calc_inputs.yres.gw.settings, 'INITIALISE', False)
        self.ctx.p2y = calc['p2y']
        return ToContext(calc)

    def prepare_calculations(self):
        self.report('setting the p2y calc as parent')
        self.ctx.calc_manager.set_parent(self.ctx.calc_inputs, self.ctx.p2y.outputs.yambo_calc_folder)

if __name__ == "__main__":
    pass
