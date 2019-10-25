# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from boh import managers #########################

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.conv_utils import convergence_evaluation, take_gw_gap, last_conv_calc_recovering

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
        spec.input("fit_options", valid_type=Dict, required=True, \
                    help = 'fit to converge: 1/x or e^-x') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
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
        """Initialize the workflow""" #meglio fare prima un conto di prova? almeno se nn ho un parent folder magari... giusto per non fare dei quantum espresso di continuo...pero' mesh? rischio


        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints = self.inputs.kpoints
        self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints
        try:
            self.ctx.calc_inputs.parent_folder = self.inputs.parent_folder
        except:
            pass


        self.ctx.workflow_manager = workflow_manager(self.inputs.var_to_conv.get_list())
        self.ctx.workflow_manager.converged = False
        self.ctx.workflow_manager.fully_converged = False

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop())
        self.ctx.calc_manager.iter  = 1

        try: #qualcosa di meglio...--> voglio un find mesh qui...col metodo
            self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
        except:
            pass

        self.ctx.first_calc = True

        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.act_var['var']))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.workflow_manager.fully_converged:
            self.report('Convergence finished')
            return False

        if self.ctx.calc_manager.iter  > self.ctx.calc_manager.max_restarts:
            self.report('Convergence failed due to max restarts exceeded for variable {}'.format(self.ctx.calc_manager.var))
            return False

        elif self.ctx.workflow_manager.converged:
            #update variable
            self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop())
            try:
                self.ctx.k_distance = self.ctx.calc_manager.starting_k_distance
            except:
                pass
            self.ctx.calc_manager.iter = 1
            self.ctx.workflow_manager.converged = False
            self.report('Next variable to converge: {}'.format(self.ctx.calc_manager.var))
            return True
        elif not self.ctx.workflow_manager.converged:
            self.report('Convergence on {}'.format(self.ctx.calc_manager.var))
            return True
        else:
            self.report('Undefined state on {}'.format(self.ctx.calc_manager.var))
            return False


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        calc = {}

        self.ctx.calc_manager.values = []

        for i in range(self.ctx.calc_manager.steps):

            self.report('Preparing iteration number {} on {}'.\
                format(i+(self.ctx.calc_manager.iter-1)*self.ctx.calc_manager.steps+1,self.ctx.calc_manager.var))

            if i == 0 and self.ctx.first_calc:
                self.report('first calc will be done with the starting params')
                first = 0 #it is the first calc, I use it's original values
            else: #the true flow
                first = 1

            self.ctx.calc_inputs, value = self.ctx.calc_manager.updater(self.ctx.calc_inputs, self.ctx.k_distance)
            self.calc_manager.values.append(value)


            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            self.calc_manager.wfl_pk = future.pk

        return ToContext(future)


    def conv_eval(self):


        self.report('Convergence evaluation, we will try to parse some result')
        convergence_evaluator = convergence_evaluator(self.ctx.calc_manager.conv_window, self.ctx.calc_manager.conv_thr)
        try:
            quantities = self.ctx.calc_manager.take_quantities()
            converged, oversteps = convergence_and_backtracing(quantities[:,1])

            for i in range(self.ctx.act_var['steps']):

                self.absolute_story.append(self.calc_manager)

            if converged:

                self.ctx.converged = True

                #taking as starting point just the first of the convergence window...
                last_ok_pk, oversteps = last_conv_calc_recovering(self.ctx.act_var,gaps[-1,1],'gap',self.ctx.conv_var)
                self.report('oversteps:{}'.format(oversteps))

                self.ctx.conv_var = self.ctx.conv_var[:-oversteps]

                last_ok_pk = load_node(self.ctx.conv_var[-1][-2]).caller.caller.pk

                last_ok = load_node(last_ok_pk)
                self.ctx.calc_inputs.yres.gw.parameters = last_ok.get_builder_restart().yres.gw['parameters'] #valutare utilizzo builder restart nel loop!!
                self.ctx.calc_inputs.scf.kpoints = last_ok.get_builder_restart().scf.kpoints #sistemare xk dovrebbe tornare alla density a conv... non lo farà ...  capire
                self.ctx.calc_inputs.parent_folder = last_ok.outputs.yambo_calc_folder

                if self.ctx.act_var['var'] == 'kpoints':
                    self.ctx.k_distance = self.ctx.k_distance - self.ctx.act_var['delta']*oversteps

                self.report('Convergence on {} reached in {} calculations, the gap is {}' \
                            .format(self.ctx.act_var['var'], self.ctx.act_var['steps']*self.ctx.act_var['iter'], self.ctx.conv_var[-1][-3] ))


            else:
                self.ctx.converged = False
                self.report('Convergence on {} not reached yet in {} calculations' \
                            .format(self.ctx.act_var['var'], self.ctx.act_var['steps']*(self.ctx.act_var['iter'] )))
                self.ctx.calc_inputs.parent_folder = load_node(self.ctx.act_var['wfl_pk']).outputs.yambo_calc_folder


            if self.ctx.variables == [] : #variables to be converged are finished

                self.ctx.fully_converged = True
        except:
            self.report('problem during the convergence evaluation, the workflows will stop and collect the previous info, so you can restart from there')
            self.report('if no datas are parsed: are you sure of your convergence windows?')
            self.report('the error was: {}'.format(str(traceback.format_exc()))) #debug
            self.ctx.fully_converged = True

        self.ctx.calc_manager.iter  += 1
        self.ctx.first_calc = False


    def report_wf(self): #mancano le unita'

        self.report('Final step. The workflow now will collect some info about the calculations in the "calc_info" output node ')

        #self.ctx.conv_var = (list(self.ctx.act_var.keys())+['calc_number','params_vals','gap']).append(self.ctx.conv_var)

        self.report('Converged variables: {}'.format(self.ctx.conv_var))
        #inserire una lista finale dei parametri di convergenza...xk la storia potrebbe non essere sufficiente, perdo delle partenze..
        converged_var = List(list=self.ctx.conv_var).store()
        all_var = List(list=self.ctx.all_calcs).store()
        self.out('conv_info', converged_var)
        self.out('all_calcs_info', all_var)

if __name__ == "__main__":
    pass
