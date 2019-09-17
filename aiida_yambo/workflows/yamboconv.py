# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import Dict

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yamborwf import YamboWorkflow

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboWorkflow, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl')

        spec.input("variables", valid_type=Dict, required=False, \
                    help = 'variables to converge, range and steps')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                     while_(cls.not_converged)(
                     cls.next_step,
                     cls.conv_eval),
                     cls.report_wf,
                     )

##################################################################################

        #spec.output('yambo_calc_folder', valid_type = RemoteData,
            #help='The final yambo calculation remote folder.')

    def start_workflow(self):
        """Initialize the workflow"""


        self.ctx.variables = self.inputs.variables.get_dict()
        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.converged = False
        self.ctx.fully_converged = False

        self.report("workflow initilization step completed.")

    def not_converged(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""

        if self.ctx.converged and self.ctx.fully_converged:
            self.report('the workflow is finished')
            return False

        elif not self.ctx.converged:
            self.report('still trying same variable convergence')
            #update params

            return True

        elif self.ctx.converged and not  self.ctx.fully_converged:
            self.report('next variable to converge')
            #update variable
            return True


    def next_step(self):
        """This function  will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        self.ctx.delta = self.ctx.variables[str(self.ctx.act_var)]['delta']
        self.ctx.steps = self.ctx.variables[str(self.ctx.act_var)]['steps']

        for i in range(self.ctx.steps):

            self.ctx.inputs[self.ctx.act_var] = self.ctx.inputs[self.ctx.act_var] + i*self.ctx.delta
            future = self.submit(YamboWorkflow, **self.ctx.inputs)
            calc[i] = future


        return ToContext(**calc)

    def conv_eval(self):

        self.report('convergence evaluation')
       
        #self.ctx.converged = True or # NOTE:

        #if all var are ok: self.ctx.fully_converged = True

    def report_wf(self):

        self.report('Final step.')

        calc = self.ctx.calc

if __name__ == "__main__":
    pass
