# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import Dict, Str, KpointsData, RemoteData

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.utils.mapping import update_mapping

from aiida_yambo.workflows.yambowf import YamboWorkflow

class YamboConvergence(WorkChain):

    """This workflow will perform yambo convergences with the respect to the gap at gamma... In future for multiple k points.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboConvergence, cls).define(spec)

        spec.expose_inputs(YamboWorkflow, namespace='ywfl', exclude = ('scf.kpoints', 'nscf.kpoints','parent_folder'))

        spec.input('kpoints', valid_type=KpointsData, required = True)
        spec.input('parent_folder', valid_type=RemoteData, required = False)

        spec.input("var_to_conv", valid_type=Dict, required=False, \
                    help = 'variables to converge, range, steps, and max restarts')
        spec.input("fit_options", valid_type=Dict, required=True, \
                    help = 'fit to converge: 1/x or e^-x') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.has_to_continue)(
                    cls.next_step), #cls.conv_eval
                    cls.report_wf,
                    )

##################################################################################

        #spec.output('convergence_history', valid_type = Str,
            #help='The convergence path.')
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

        self.ctx.variables = self.inputs.var_to_conv.get_dict()
        self.ctx.act_var = self.ctx.variables.popitem()
        self.ctx.max_restarts = self.ctx.act_var[1]['max_restarts'] #for the actual variable!
        self.ctx.conv_thr = self.ctx.act_var[1]['conv_thr'] #threeshold
        self.ctx.conv_window = self.ctx.act_var[1]['conv_window'] #conv_window: previous n calcs


        self.ctx.converged = False
        self.ctx.fully_converged = False


        self.ctx.iter = 0


        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.act_var[0]))

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
                self.ctx.calc_inputs.parent_folder = self.ctx.calc[str(self.ctx.steps)].outputs.parent_folder #start from the converged / last calculation
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

        calc = {}
        for i in range(self.ctx.steps):   #this is ok for simple scalar parameters... try to figure out for list..

            if self.ctx.act_var[0] == 'bands': #bands!!  e poi dovrei fare insieme le due bande...come fare? magari
                                                 #metto 'bands' come variabile e lo faccio automaticamente il cambio doppio....

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params['BndsRnXp'][-1] = self.ctx.new_params['BndsRnXp'][-1] + i*self.ctx.delta
                self.ctx.new_params['GbndRnge'][-1] = self.ctx.new_params['GbndRnge'][-1] + i*self.ctx.delta

                self.ctx.calc_inputs.yres.gw.parameters = update_mapping(self.ctx.calc_inputs.yres.gw.parameters, self.ctx.new_params)

            elif str(self.ctx.act_var[0]) == 'kpoints': #meshes are different, so I need to do YamboWorkflow from scf (scratch).

                from aiida_yambo.workflows.utils.inp_gen import get_updated_mesh
                self.ctx.calc_inputs.scf.kpoints = get_updated_mesh(self.inputs.kpoints, i, self.ctx.delta)
                self.ctx.calc_inputs.nscf.kpoints = self.ctx.calc_inputs.scf.kpoints
                try:
                    del self.ctx.calc_inputs.parent_folder  #I need to start from scratch...non sono sicuro si faccia cosi'
                except:
                    pass #just for the first iteration we have a parent_folder

            else: #"scalar" quantity

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params[str(self.ctx.act_var[0])] = self.ctx.new_params[str(self.ctx.act_var[0])] + i*self.ctx.delta

                self.ctx.calc_inputs.yres.gw.parameters = update_mapping(self.ctx.calc_inputs.yres.gw.parameters, self.ctx.new_params)



            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i)] = future         #va cambiata eh!!! o forse no...

        return ToContext(**calc)

    '''
    def conv_eval(self):

        self.report('convergence evaluation')

        converged = conv_eval(self.ctx.conv_thr, self.ctx.conv_window, self.ctx.calc)

        if converged:
            conv_fit = fit_eval(self.ctx.conv_thr, self.input.fit_options, self.ctx.calc)

        if converged and conv_fit:
            self.ctx.converged = True
        else:
            self.ctx.converged = False

    '''
    def report_wf(self):

        self.report('Final step.')
        self.report('Converged variables:')
        #Dict with converged params

if __name__ == "__main__":
    pass
