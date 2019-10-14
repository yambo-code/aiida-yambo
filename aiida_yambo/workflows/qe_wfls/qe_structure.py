# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwRelaxWorkChain
from aiida_quantumespresso.utils.mapping import update_mapping

from aiida_yambo.workflows.utils.conv_utils import convergence_evaluation, take_qe_total_energy

class QE_relax(WorkChain):

    """This workflow will perform structure relaxation both relax and vc-relax
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(QE_relax, cls).define(spec)

        spec.expose_inputs(PwRelaxWorkChain, namespace='relax', namespace_options={'required': True},\
                            exclude={'structure'})

        spec.input("initial_structure", valid_type=StructureData, required=True, \
                    help = 'initial structure') #many possibilities, also to define by hand the fitting functions.

        spec.input("conv_options", valid_type=Dict, required=True, \
                    help = 'options for the relaxation: a vc-relax with ecutwf conv or step by step relaxation') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.conv_eval),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('conv_info', valid_type = List, help='list with convergence path')
        spec.output('relaxed_structure', valid_type = Structure, help='the final structure')

    def start_workflow(self):
        """Initialize the workflow""" #meglio fare prima un conto di prova? almeno se nn ho un parent folder magari... giusto per non fare dei quantum espresso di continuo...pero' mesh? rischio


        self.ctx.calc_inputs = self.exposed_inputs(PwRelaxWorkChain, 'relax')

        self.ctx.conv_options = self.inputs.conv_options.get_dict()

        self.ctx.fully_relaxed = False

        self.ctx.iter = 1

        self.ctx.all_calcs = []
        self.ctx.conv_var = []

        self.ctx.first_calc = True

        self.report("workflow initilization step completed, the relaxation scheme will be {}.".format(self.ctx.calc_inputs.relaxation_scheme))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.iter  > self.ctx.conv_options  ['max_restarts'] and not self.ctx.converged:   #+1 because it starts from zero
            self.report('the workflow is failed due to max restarts exceeded for variable {}'.format(self.ctx.act_var['var']))
            return False

        elif self.ctx.fully_relaxed:
            self.report('the workflow is finished successfully')
            return False

        elif not self.ctx.fully_relaxed:
            self.report('the workflow is not finished')
            return True


    def next_step(self):
        """This function will submit the next step"""

        calc = {}

        self.ctx.param_vals = []

        for i in range(self.ctx.conv_options['steps']):

            self.report('Preparing iteration number {} on {}'.format(i+self.ctx.iter*self.ctx.conv_options['steps']))

                if i == 0 and self.ctx.first_calc and i == 0:
                    self.report('first calc will be done with the starting params')
                    first = 0 #it is the first calc, I use it's original values
                else: #the true flow
                    first = 1

                if self.ctx.calc_inputs.relaxation_scheme == 'relax':

                    scaled_structure = self.inputs.structure.get_ase()
                    scaled_structure.set_cell(scaled_structure.cell*(1.0+0.01*(i+first)*self.ctx.iter), scale_atoms=True)
                    self.ctx.calc_inputs.structure = StructureData(ase=scaled_structure)
                    self.report('lattice-variation used: {}%'.format())

                    self.ctx.param_vals.append(0.01*i)

                else self.ctx.calc_inputs.relaxation_scheme == 'vc-relax':

                    self.ctx.new_params = self.ctx.calc_inputs.base.pw.parameters.get_dict()
                    self.ctx.new_params['SYSTEM']['ecutwf'] = self.ctx.new_params['SYSTEM']['ecutwf'] + self.ctx.act_var['delta']*first

                    self.ctx.calc_inputs.base.pw.parameters = update_mapping(self.ctx.calc_inputs.base.pw.parameters, self.ctx.new_params)

                    self.ctx.param_vals.append(self.ctx.new_params['SYSTEM'][str(self.ctx.act_var['var'])])

            future = self.submit(PwRelaxWorkChain, **self.ctx.calc_inputs)
            calc[str(i+1)] = future        #va cambiata eh!!! o forse no...forse basta mettere future
            self.ctx.wfl_pk = future.pk

        return ToContext(calc) #questo aspetta tutti i calcoli


    def conv_eval(self):

        self.ctx.first_calc = False
        self.report('Convergence evaluation')

        try:

            if self.ctx.calc_inputs.relaxation_scheme == 'vc-relax':

                converged, etot = convergence_evaluation(self.ctx.act_var,take_qe_total_energy(self.ctx.act_var,self.ctx.k_last_dist)) #redundancy..

            elif self.ctx.calc_inputs.relaxation_scheme == 'relax':

                converged, etot = relaxation_evaluation(self.ctx.act_var,take_qe_total_energy(self.ctx.act_var,self.ctx.k_last_dist)) #redundancy..

            for i in range(self.ctx.conv_options['steps']):

                self.ctx.all_calcs.append([len(load_node(self.ctx.wfl_pk).caller.called)-self.ctx.conv_options['steps']+i, \
                                    self.ctx.param_vals[i], etot[i,1], int(etot[i,2]), str(converged)]) #tracking the whole iterations and etot

                self.ctx.conv_var.append([len(load_node(self.ctx.wfl_pk).caller.called)-self.ctx.conv_options['steps']+i, \
                                    self.ctx.param_vals[i], etot[i,1], int(etot[i,2]), str(converged)]) #tracking the whole iterations and etot
            if converged:

                self.ctx.fully_relaxed = True

                self.report('Relaxation scheme {} completed in {} calculations, the total energy is {}' \
                            .format(self.inputs.relaxation_scheme, self.ctx.conv_options['steps']*self.ctx.iter, etot[-self.ctx.conv_options['conv_window'], 1] ))


            else:

                self.ctx.fully_relaxed = False
                self.report('Relaxation scheme {} not completed yet in {} calculations' \
                            .format(self.ctx.act_var['var'], self.ctx.act_var['steps']*(self.ctx.act_var['iter'] )))
                self.ctx.calc_inputs.pw.parent_folder = load_node(self.ctx.act_var['wfl_pk']).called[0].outputs.remote_folder

        except:
            self.report('problem during the min/convergence evaluation, the workflows will stop and collect the previous info, so you can restart from there')
            self.report('the error was: {}'.format(str(traceback.format_exc()))) #debug
            self.ctx.fully_relaxed = True

        self.ctx.iter  += 1

    def report_wf(self):

        self.report('Final step. The workflow now will collect some info about the calculations in the "calc_info" output node ')

        #self.ctx.conv_var = (list(self.ctx.act_var.keys())+['calc_number','params_vals','gap']).append(self.ctx.conv_var)

        self.report('Relaxation scheme performed: {}'.format(self.inputs.relaxation_scheme))

        converged_var = List(list=self.ctx.conv_var).store()
        all_var = List(list=self.ctx.all_calcs).store()
        self.out('conv_info', converged_var)
        self.out('all_calcs_info', all_var)
        self.out('relaxed_structure',relaxed!)

if __name__ == "__main__":
    pass
