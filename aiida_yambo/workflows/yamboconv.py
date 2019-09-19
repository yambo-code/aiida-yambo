# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import Dict

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yambowf import YamboWorkflow

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl')

        spec.input("variables", valid_type=Dict, required=False, \
                    help = 'variables to converge, range, steps, and max restarts')
        spec.input("fit_type", valid_type=Str, required=False, default='1/x', \
                    help = 'fit to converge: of 1/x or e^-x')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.conv_eval),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('yambo_calc_folder', valid_type = RemoteData,
            help='The final yambo calculation remote folder.')

    def start_workflow(self):
        """Initialize the workflow"""


        self.ctx.variables = self.inputs.variables.get_dict()
        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.converged = False
        self.ctx.fully_converged = False
        self.ctx.act_var = self.ctx.variables.popitem()
        self.ctx.max_restarts = self.ctx.act_var[1]['max_restarts'] #for the actual variable!
        self.ctx.conv_thr = self.ctx.act_var[1]['conv_thr'] #threeshold
        self.ctx.conv_window = self.ctx.act_var[1]['conv_window'] #conv_window: previous n calcs
        self.ctx.iter = 0
        
        self.report("workflow initilization step completed.")

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.act_var == {} or self.ctx.iter >= self.ctx.max_restarts:
            return False

        else:

            if self.ctx.converged and self.ctx.fully_converged:
                self.report('the workflow is finished')
                return False

            elif not self.ctx.converged:
                self.report('still trying same variable convergence')
                self.ctx.iter += 1
                return True

            elif self.ctx.converged and not self.ctx.fully_converged:
                self.report('next variable to converge')
                #update variable
                self.ctx.iter = 0
                self.ctx.act_var = self.ctx.variables.popitem()
                self.ctx.max_restarts = self.ctx.act_var[1]['max_restarts']
                self.ctx.conv_thr = self.ctx.act_var[1]['conv_thr']
                self.ctx.conv_window = self.ctx.act_var[1]['conv_window']
                return True


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        self.ctx.delta = self.ctx.act_var[1]['delta']
        self.ctx.steps = self.ctx.act_var[1]['steps']

        for i in range(self.ctx.steps):   #this is ok for simple scalar parameters... try to figure out for list..

            if type(self.ctx.act_var[0]) == list: #bands!!

                self.ctx.inputs[str(self.ctx.act_var[0][-1])] = self.ctx.inputs[str(self.ctx.act_var[0][-1])] + i*self.ctx.delta

            elif str(self.ctx.act_var[0]) == 'kpoints': #meshes are different.

                from aiida_yambo.workflows.utils.inp_gen import get_updated_mesh
                self.ctx.inputs[str(self.ctx.act_var[0])] = get_updated_mesh(self.ctx.inputs[str(self.ctx.act_var[0])], i, self.ctx.delta)

            else: #scalar
                self.ctx.inputs[str(self.ctx.act_var[0])] = self.ctx.inputs[str(self.ctx.act_var[0])] + i*self.ctx.delta

            future = self.submit(YamboWorkflow, **self.ctx.inputs)
            calc[i] = future


        return ToContext(**calc)

'''
    def conv_eval(self):

        self.report('convergence evaluation')

        converged = conv_eval(self.ctx.conv_thr, self.ctx.conv_window, self.ctx.calc)

        if converged:
            conv_fit = fit_eval(self.ctx.conv_thr, self.input.fit_type, self.ctx.calc)

        if converged and conv_fit:
            self.ctx.converged = True
        else:
            self.ctx.converged = False


    def report_wf(self):

        self.report('Final step.')
        self.report('Converged variables:')
        #Dict with converged params
'''
if __name__ == "__main__":
    pass
