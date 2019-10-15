# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

from aiida.orm import Int, Dict, Str, KpointsData, StructureData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_, if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.mapping import update_mapping

from aiida_yambo.workflows.utils.conv_utils import relaxation_evaluation

class QE_relax(WorkChain):

    """This workflow will perform structure relaxation both relax and vc-relax
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(QE_relax, cls).define(spec)

        spec.expose_inputs(PwBaseWorkChain, namespace='base', namespace_options={'required': True},\
                            exclude= ['pw.structure',])

        spec.input("initial_structure", valid_type=StructureData, required=True, \
                    help = 'initial structure') #many possibilities, also to define by hand the fitting functions.

        spec.input("conv_options", valid_type=Dict, required=True, \
                    help = 'options for the relaxation: a vc-relax with ecutwfc conv or step by step relaxation') #many possibilities, also to define by hand the fitting functions.

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.has_to_continue)(
                    cls.next_step,
                    cls.conv_eval,
                    ),
                    if_(cls.can_do_scf)(
                    cls.do_final_scf),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('path', valid_type = List, help='list with convergence path')
        spec.output('relaxed_scf', valid_type = Int, help='the final structure')

    def start_workflow(self):
        """Initialize the workflow""" #meglio fare prima un conto di prova? almeno se nn ho un parent folder magari... giusto per non fare dei quantum espresso di continuo...pero' mesh? rischio


        self.ctx.calc_inputs = self.exposed_inputs(PwBaseWorkChain, 'base')

        self.ctx.conv_options = self.inputs.conv_options.get_dict()

        self.ctx.fully_relaxed = False

        self.ctx.conv_options['iter']= 1

        self.ctx.path = []

        self.ctx.first_calc = True

        self.ctx.optimal_value = 0

        self.ctx.fully_relaxed_to_scf = False

        self.ctx.params = []

        self.report("workflow initilization step completed, the relaxation scheme will be {}.".format(self.ctx.conv_options['relaxation_scheme']))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.conv_options['iter'] > self.ctx.conv_options['max_restarts'] and not self.ctx.fully_relaxed:
            self.report('the workflow is failed due to max restarts exceeded')
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

            self.report('Preparing iteration number {}'.format(i+(self.ctx.conv_options['iter']-1)*self.ctx.conv_options['steps']+1))

            if i == 0 and self.ctx.first_calc:
                self.report('first calc will be done with the starting params')
                first = 0 #it is the first calc, I use it's original values
            else: #the true flow
                first = 1

            if self.ctx.conv_options['relaxation_scheme'] == 'relax':

                variation = 0.01*(i-self.ctx.conv_options['steps']//2)*self.ctx.conv_options['iter']#-1 0 1, -2 2 ....
                if variation == 0 and not self.ctx.first_calc:
                    continue #next iter, so avoiding the "center" of the variations, 0
                else:
                    scaled_structure = self.inputs.initial_structure.get_ase()
                    scaled_structure.set_cell(scaled_structure.cell*(1.0+variation), scale_atoms=True)
                    self.ctx.calc_inputs.pw.structure = StructureData(ase=scaled_structure)
                    self.report('lattice-variation used: {}%'.format(variation))

                self.ctx.param_vals.append(variation)

            elif self.ctx.conv_options['relaxation_scheme'] == 'vc-relax':

                self.ctx.calc_inputs.pw.structure = self.inputs.initial_structure

                future = self.submit(PwBaseWorkChain, **self.ctx.calc_inputs)
                calc[str(i+1)] = future
                break #just one calc

            future = self.submit(PwBaseWorkChain, **self.ctx.calc_inputs)
            calc[str(i+1)] = future        #va cambiata eh!!! o forse no...forse basta mettere future
            self.ctx.conv_options['wfl_pk'] = future.pk

        return ToContext(calc) #questo aspetta tutti i calcoli


    def conv_eval(self):

        self.ctx.first_calc = False
        self.report('Convergence evaluation')

        try:

            if self.ctx.conv_options['relaxation_scheme'] == 'vc-relax': #actually it serves as a convergence tool for ecutwfc, the next step is the kpoint conv and a final scf

                return

            elif self.ctx.conv_options['relaxation_scheme'] == 'relax': #da sistemare..

                try:
                    converged, etot, min = relaxation_evaluation(self.ctx.param_vals,self.ctx.conv_options) #redundancy..
                    self.ctx.optimal_value = min
                    self.report('the fit was successful, the minimum will be {}'.format(self.ctx.optimal_value))
                    for i in range(self.ctx.conv_options['steps']):

                        self.ctx.path.append([len(load_node(self.ctx.conv_options['wfl_pk']).caller.called)-self.ctx.conv_options['steps']+i, \
                                            self.ctx.param_vals[i], etot[i,1], int(etot[i,2]), str(converged)]) #tracking the whole iterations and etot
                except:
                    converged = False
                    self.report('the fit was not successful, we will try to enlarge the region')

            if converged:

                self.ctx.fully_relaxed = True
                self.ctx.fully_relaxed_to_scf = True

                if self.ctx.conv_options['relaxation_scheme'] == 'vc-relax':
                    self.report('Relaxation scheme {} completed'.format(self.ctx.conv_options['relaxation_scheme']))
                    return

                self.report('Relaxation scheme {} completed in {} calculations, the optimal value for your relaxed structure is {}' \
                            .format(self.ctx.conv_options['relaxation_scheme'], self.ctx.conv_options['steps']*self.ctx.conv_options['iter'], self.ctx.optimal_value))

            else:

                self.ctx.fully_relaxed = False
                self.report('Relaxation scheme {} not completed yet in {} calculations' \
                            .format(self.ctx.conv_options['relaxation_scheme'], self.ctx.conv_options['steps']*(self.ctx.conv_options['iter'])))
                #self.ctx.calc_inputs.pw.parent_folder = load_node(self.ctx.conv_options['wfl_pk']).called[0].outputs.remote_folder

        except:
            self.report('problem during the min/convergence evaluation, the workflows will stop and collect the previous info, so you can restart from there')
            self.report('the error was: {}'.format(str(traceback.format_exc()))) #debug
            self.ctx.fully_relaxed = True
            self.ctx.fully_relaxed_to_scf = False

        self.ctx.conv_options['iter'] += 1

    def can_do_scf(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.fully_relaxed_to_scf:
            self.report('the workflow is finished successfully, now we do a scf')
            return True

    def do_final_scf(self):

        scf = {}
        if self.ctx.conv_options['relaxation_scheme'] == 'vc-relax':

            inputs_scf = load_node(self.ctx.last_ok_pk).get_builder_restart()
            inputs_scf['pw']['parameters']['CONTROL']['calculation'] = 'scf'
            inputs_scf['pw']['structure'] = load_node(self.ctx.last_ok_pk).called[0].outputs.output_structure
            scf = self.submit(PwBaseWorkChain, **inputs_scf)

        elif self.ctx.conv_options['relaxation_scheme'] == 'relax':

            inputs_scf = load_node(self.ctx.conv_options['wfl_pk']).get_builder_restart()
            inputs_scf['pw']['parameters']['CONTROL']['calculation'] = 'relax'
            scaled_structure = self.inputs.initial_structure.get_ase()
            scaled_structure.set_cell(scaled_structure.cell*(1.0+self.ctx.optimal_value), scale_atoms=True)
            inputs_scf['pw']['structure']= StructureData(ase=scaled_structure)
            future = self.submit(PwBaseWorkChain, **inputs_scf)
            scf[self.ctx.conv_options['relaxation_scheme']] = future

        return ToContext(scf)

    def report_wf(self):

        self.report('Final step. The workflow now will collect some info about the calculations in the "path" output node, and the relaxed scf calc')

        self.report('Relaxation scheme performed: {}'.format(self.ctx.conv_options['relaxation_scheme']))

        path = List(list=self.ctx.path).store()
        rel_scf = Int(self.ctx.scf.pk).store()
        self.out('path', path)

        self.out('relaxed_scf', rel_scf)


if __name__ == "__main__":
    pass
