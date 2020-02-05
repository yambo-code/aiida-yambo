# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_ , if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.helpers import *

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

        spec.input("var_to_conv", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max restarts')
        spec.input("fit_options", valid_type=Dict, required=False, \
                    help = 'fit to converge: 1/x or e^-x') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    if_(cls.p2y_needed)(
                    cls.do_p2y,
                    cls.prepare_convergences,
                    ),
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.conv_eval),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('conv_info', valid_type = List, help='list with convergence path')
        spec.output('all_calcs_info', valid_type = List, help='all calculations')
        #plots of single and multiple convergences, with data.txt to plot whenever you want
        #fitting just the last conv window, but plotting all

    def start_workflow(self):
        """Initialize the workflow"""

        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints = self.inputs.kpoints
        self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints

        self.ctx.workflow_manager = workflow_manager(self.inputs.var_to_conv.get_list())
        self.ctx.workflow_manager.global_step = 0
        self.ctx.workflow_manager.fully_converged = False

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop())
        self.ctx.calc_manager.type = 'yambo.yambo'
        self.ctx.calc_manager.iter  = 1
        self.ctx.calc_manager.converged = False

        try: #qualcosa di meglio...--> voglio un find mesh qui...col metodo
            self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
            del self.ctx.calc_manager.starting_k_distance
        except:
            self.ctx.k_distance = 1

        self.ctx.workflow_manager.first_calc = True

        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.calc_manager.var))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.workflow_manager.fully_converged:
            self.report('Convergence finished')
            return False

        if self.ctx.calc_manager.iter  > self.ctx.calc_manager.max_restarts+1:
            self.report('Convergence failed due to max restarts exceeded for variable {}'.format(self.ctx.calc_manager.var))
            return False

        elif self.ctx.calc_manager.converged:
            #update variable
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop())
            self.ctx.calc_manager.type = 'yambo.yambo'
            try:
                self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
                del self.ctx.calc_manager.starting_k_distance
            except:
                pass
            self.ctx.calc_manager.iter = 1
            self.ctx.calc_manager.converged = False
            self.report('Next variable to converge: {}'.format(self.ctx.calc_manager.var))
            return True
        elif not self.ctx.calc_manager.converged:
            self.report('Still convergence on {}'.format(self.ctx.calc_manager.var))
            return True
        else:
            self.report('Undefined state on {}'.format(self.ctx.calc_manager.var))
            return False


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        calc = {}

        self.ctx.workflow_manager.values = []

        for i in range(self.ctx.calc_manager.steps):

            self.report('Preparing iteration number {} on {}'.\
                format(i+(self.ctx.calc_manager.iter-1)*self.ctx.calc_manager.steps+1,self.ctx.calc_manager.var))

            if i == 0 and self.ctx.workflow_manager.first_calc:
                self.report('first calc will be done with the starting params')
                first = 0 #it is the first calc, I use it's original values
            else: #the true flow
                first = 1

            self.ctx.calc_inputs, value = self.ctx.calc_manager.updater(self.ctx.calc_inputs, self.ctx.k_distance,first)

            if self.ctx.calc_manager.var == 'kpoints':
                self.ctx.k_distance = value

            self.ctx.workflow_manager.values.append(value)

            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i)] = future

            self.ctx.calc_manager.wfl_pk = future.pk

        return ToContext(calc)


    def conv_eval(self):

        self.report('Convergence evaluation, we will try to parse some result')
        convergence_evaluator = the_evaluator(self.ctx.calc_manager.conv_window, self.ctx.calc_manager.conv_thr)

        try:
            quantities = self.ctx.calc_manager.take_quantities()

            if self.ctx.calc_manager.iter == 1:
                try:
                    self.ctx.workflow_manager.array_conv=np.array(self.ctx.workflow_manager.conv_story[-1][-1])
                    self.ctx.workflow_manager.array_conv = np.column_stack((self.ctx.workflow_manager.array_conv,quantities[:,:,1]))
                except:
                    self.ctx.workflow_manager.array_conv=np.array(quantities[:,:,1])
            else:
                self.ctx.workflow_manager.array_conv = np.column_stack((self.ctx.workflow_manager.array_conv,quantities[:,:,1]))

            self.report(self.ctx.workflow_manager.array_conv)
            self.ctx.calc_manager.converged, oversteps = convergence_evaluator.convergence_and_backtracing(self.ctx.workflow_manager.array_conv)

            if self.ctx.workflow_manager.first_calc:
                self.ctx.workflow_manager.absolute_story.append(['global_step']+list(self.ctx.calc_manager.__dict__.keys())+\
                            ['value', 'calc_pk','result'])
                self.ctx.workflow_manager.conv_story.append(['global_step']+list(self.ctx.calc_manager.__dict__.keys())+\
                            ['value', 'calc_pk','result'])
                self.ctx.workflow_manager.first_calc = False

            for i in range(self.ctx.calc_manager.steps):
                    self.ctx.workflow_manager.global_step += 1
                    self.ctx.workflow_manager.absolute_story.append([self.ctx.workflow_manager.global_step]+list(self.ctx.calc_manager.__dict__.values())+\
                                [self.ctx.workflow_manager.values[i], quantities[0,i,2], quantities[:,i,1]])
                    self.ctx.workflow_manager.conv_story.append([self.ctx.workflow_manager.global_step]+list(self.ctx.calc_manager.__dict__.values())+\
                                [self.ctx.workflow_manager.values[i], int(quantities[0,i,2]), quantities[:,i,1]])

            if self.ctx.calc_manager.converged:
                self.report('Success, updating the history... oversteps: {}'.format(oversteps))

                self.ctx.workflow_manager.conv_story = self.ctx.workflow_manager.conv_story[:-oversteps]

                last_ok = load_node(self.ctx.workflow_manager.conv_story[-1][-2]).caller.caller
                self.ctx.calc_inputs.yres.gw.parameters = last_ok.get_builder_restart().yres.gw['parameters']

                if self.ctx.calc_manager.var == 'kpoints':
                    self.ctx.calc_inputs.parent_folder = last_ok.outputs.yambo_calc_folder

                if self.ctx.calc_manager.var == 'kpoints':
                    self.ctx.k_distance = self.ctx.k_distance - self.ctx.calc_manager.delta*oversteps

                self.report('Convergence on {} reached in {} calculations, the gap is {}' \
                            .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter,\
                             self.ctx.workflow_manager.conv_story[-1][-1] ))

                if self.ctx.workflow_manager.true_iter == [] : #variables to be converged are finished
                     self.ctx.workflow_manager.fully_converged = True

            else:
                self.report('Convergence on {} not reached yet in {} calculations' \
                            .format(self.ctx.calc_manager.var, self.ctx.calc_manager.steps*self.ctx.calc_manager.iter))
                #self.ctx.calc_inputs.parent_folder = load_node(self.ctx.calc_manager.wfl_pk).outputs.yambo_calc_folder
        except:
            self.report('problems during the convergence evaluation, the workflows will stop and collect the previous info, so you can restart from there')
            self.report('if no datas are parsed: are you sure of your convergence window?')
            self.report('the error was: {}'.format(str(traceback.format_exc()))) #debug

        self.ctx.calc_manager.iter +=1



    def report_wf(self): #mancano le unita'

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager.fully_converged)))
        all_var = List(list=self.ctx.workflow_manager.absolute_story).store()
        converged_var = List(list=self.ctx.workflow_manager.conv_story).store()
        self.out('conv_info', converged_var)
        self.out('all_calcs_info', all_var)

    def p2y_needed(self):
        self.report('do we need a p2y??')
        try:
            self.ctx.calc_inputs.parent_folder = self.inputs.parent_folder

            try:
                parent_calc = self.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
            except:
                parent_calc = self.inputs.parent_folder.get_incoming().all_nodes()[-1]

            self.report('detecting if we need a p2y starting calculation...')
            if parent_calc.process_type=='aiida.calculations:yambo.yambo':
                self.report('no, yambo parent')
                return False
            else:
                self.report('yes, quantumespresso parent')
                return True
        except:
            self.report('yes, no parent provided')
            return True


    def do_p2y(self):
        self.report('doing the p2y')
        calc = {}
        self.report('no valid parent folder, so we will create it')
        new_settings = self.ctx.calc_inputs.yres.gw.settings.get_dict()
        new_settings['INITIALISE'] = True
        self.ctx.calc_inputs.yres.gw.settings = Dict(dict=new_settings)
        calc['p2y'] = self.submit(YamboWorkflow, **self.ctx.calc_inputs) #################run
        self.report('Submitted YamboWorkflow up to p2y, pk = {}'.format(calc['p2y'].pk))
        new_settings = self.ctx.calc_inputs.yres.gw.settings.get_dict()
        new_settings['INITIALISE'] = False
        self.ctx.calc_inputs.yres.gw.settings = Dict(dict=new_settings)
        self.ctx.p2y = calc['p2y']
        return ToContext(calc)

    def prepare_convergences(self):
        self.report('setting the p2y calc as parent')
        self.ctx.calc_inputs.parent_folder = self.ctx.p2y.outputs.yambo_calc_folder

if __name__ == "__main__":
    pass
