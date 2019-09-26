# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.utils.mapping import update_mapping

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.conv_utils import convergence_evaluation

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences with the respect to the gap at gamma... In future for multiple k points.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl', exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

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

        spec.output('calc_info', valid_type = List, help='just a check')
        #plots of single and multiple convergences, with data.txt to plot whenever you want
        #fitting just the last conv window, but plotting all

    def start_workflow(self):
        """Initialize the workflow"""


        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints = self.inputs.kpoints
        self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints
        try:
            self.ctx.calc_inputs.parent_folder = self.inputs.parent_folder
        except:
            pass
        \
        self.ctx.variables = self.inputs.var_to_conv.get_list()
        self.ctx.act_var = self.ctx.variables.pop()
        self.ctx.act_var['max_restarts'] = self.ctx.act_var['max_restarts'] #for the actual variable!

        self.ctx.converged = False
        self.ctx.fully_converged = False

        self.ctx.act_var['iter']  = 0

        self.ctx.conv_var = []

        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.act_var['var']))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.act_var['iter']  > self.ctx.act_var['max_restarts']:
            self.report('the workflow is failed due to max restarts exceeded for variable {}'.format(self.ctx.act_var['var']))
            return False

        else:

            if not self.ctx.converged:
                self.report('Convergence on {}'.format(self.ctx.act_var['var']))
                return True

            elif  self.ctx.fully_converged:
                self.report('the workflow is finished successfully')
                return False

            elif self.ctx.converged and not self.ctx.fully_converged:
                #update variable
                self.ctx.calc_inputs.parent_folder = load_node(self.ctx.act_var['wfl_pk']).called[-1].outputs.last_calc_folder #start from the converged / last calculation
                self.ctx.act_var = self.ctx.variables.pop()
                self.ctx.act_var['gaps'] = []
                self.ctx.act_var['iter']  = 0
                self.report('next variable to converge: {}'.format(self.ctx.act_var['var']))
                return True


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        calc = {}

        t = 0
        if self.ctx.act_var['iter']  > 0:   #this is done in order to avoid to have the same calculation at the end and at the beginning of to consecutive next_step
            t = 1

        self.ctx.param_vals = []

        for i in range(0, self.ctx.act_var['steps']):

            if self.ctx.act_var['var'] == 'bands': #bands!!  e poi dovrei fare insieme le due bande...come fare? magari
                                                 #metto 'bands' come variabile e lo faccio automaticamente il cambio doppio....

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params['BndsRnXp'][-1] = self.ctx.new_params['BndsRnXp'][-1] + (i+t)*self.ctx.act_var['delta']
                self.ctx.new_params['GbndRnge'][-1] = self.ctx.new_params['GbndRnge'][-1] + (i+t)*self.ctx.act_var['delta']

                self.ctx.calc_inputs.yres.gw.parameters = update_mapping(self.ctx.calc_inputs.yres.gw.parameters, self.ctx.new_params)

                self.ctx.param_vals.append(self.ctx.new_params['GbndRnge'][-1])

            elif self.ctx.act_var['var'] == 'kpoints': #meshes are different, so I need to do YamboWorkflow from scf (scratch).

                from aiida_yambo.workflows.utils.inp_gen import get_updated_mesh
                self.ctx.calc_inputs.scf.kpoints = get_updated_mesh(self.inputs.kpoints, i+t, self.ctx.act_var['delta'])
                self.ctx.calc_inputs.nscf.kpoints = self.ctx.calc_inputs.scf.kpoints
                try:
                    del self.ctx.calc_inputs.parent_folder  #I need to start from scratch...non sono sicuro si faccia cosi'
                except:
                    pass #just for the first iteration we have a parent_folder

                self.ctx.param_vals.append(self.ctx.calc_inputs.nscf.kpoints.get_kpoints_mesh()[0])

            else: #"scalar" quantity

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params[str(self.ctx.act_var['var'])] = self.ctx.new_params[str(self.ctx.act_var['var'])] + (i+t)*self.ctx.act_var['delta']

                self.ctx.calc_inputs.yres.gw.parameters = update_mapping(self.ctx.calc_inputs.yres.gw.parameters, self.ctx.new_params)

                self.ctx.param_vals.append(self.ctx.new_params[str(self.ctx.act_var['var'])])


            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i+1)] = future        #va cambiata eh!!! o forse no...forse basta mettere future
            self.ctx.act_var['wfl_pk'] = future.pk

        return ToContext(calc) #questo aspetta tutti i calcoli


    def conv_eval(self):

        self.report('Convergence evaluation')

        self.ctx.act_var['iter']  += 1

        converged, gap = convergence_evaluation(self.ctx.act_var)


        if converged:

            self.ctx.converged = True
            self.report('Convergence on {} reached in {} calculations' \
                        .format(self.ctx.act_var['var'], self.ctx.act_var['steps']*(self.ctx.act_var['iter'] )))

        else:
            self.ctx.converged = False
            self.report('Convergence on {} not reached yet in {} calculations' \
                        .format(self.ctx.act_var['var'], self.ctx.act_var['steps']*(self.ctx.act_var['iter'] )))

        if self.ctx.variables == [] : #variables to be converged are finished

            self.ctx.fully_converged = True

        for i in range(1,self.ctx.act_var['steps']+1):

            self.ctx.conv_var.append(list(self.ctx.act_var.values())+ \
                            [len(self.ctx.act_var['wfl_pk']).caller-self.ctx.act_var['steps']+i, self.ctx.param_vals[i], gap[i], self.ctx.param_vals[i]]) #tracking the whole iterations and gaps


    def report_wf(self):

        self.report('Final step. The workflow now will collect some info about the calculations in the "calc_info" output node ')

        self.ctx.conv_var = (list(self.ctx.act_var.keys())+['calc_number','params_vals','gap']).append(self.ctx.conv_var)

        self.report('Converged variables: {}'.format(self.ctx.conv_var))

        converged_var = List(list=self.ctx.conv_var).store()
        self.out('calc_info', converged_var)

if __name__ == "__main__":
    pass
