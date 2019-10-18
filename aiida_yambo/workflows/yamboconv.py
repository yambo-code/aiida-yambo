# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit


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
        \
        self.ctx.variables = self.inputs.var_to_conv.get_list()
        self.ctx.act_var = self.ctx.variables.pop()
        #self.ctx.act_var['max_restarts'] = self.ctx.act_var['max_restarts'] #for the actual variable!

        self.ctx.converged = False
        self.ctx.fully_converged = False

        self.ctx.act_var['iter']  = 1

        self.ctx.all_calcs = []
        self.ctx.conv_var = []

        self.ctx.first_calc = True
        try:
            self.ctx.k_last_dist = self.ctx.act_var['starting_mesh_density']
        except:
            pass

        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.act_var['var']))

    def has_to_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""
        if self.ctx.act_var['iter']  > self.ctx.act_var['max_restarts'] and not self.ctx.converged and not self.ctx.fully_converged:   #+1 because it starts from zero
            self.report('the workflow is failed due to max restarts exceeded for variable {}'.format(self.ctx.act_var['var']))
            return False

        else:

            if not self.ctx.converged:
                self.report('Convergence on {}'.format(self.ctx.act_var['var']))
                return True

            elif self.ctx.fully_converged:
                self.report('the workflow is finished successfully')
                return False

            elif self.ctx.converged and not self.ctx.fully_converged:
                #update variable
                self.ctx.act_var = self.ctx.variables.pop()
                self.ctx.act_var['iter']  = 1
                self.ctx.converged = False
                self.report('next variable to converge: {}'.format(self.ctx.act_var['var']))
                return True


    def next_step(self):
        """This function will submit the next step"""

        #loop on the given steps of a given variable to make convergence

        calc = {}

        self.ctx.param_vals = []

        for i in range(self.ctx.act_var['steps']):

            self.report('Preparing iteration number {} on {}'.format(i+(self.ctx.act_var['iter']-1)*self.ctx.act_var['steps']+1,self.ctx.act_var['var']))

            if i == 0 and self.ctx.first_calc:
                self.report('first calc will be done with the starting params')
                first = 0 #it is the first calc, I use it's original values
            else: #the true flow
                first = 1


            if self.ctx.act_var['var'] == 'bands': #bands!!  e poi dovrei fare insieme le due bande...come fare? magari
                                                 #metto 'bands' come variabile e lo faccio automaticamente il cambio doppio....

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params['BndsRnXp'][-1] = self.ctx.new_params['BndsRnXp'][-1] + self.ctx.act_var['delta']*first
                self.ctx.new_params['GbndRnge'][-1] = self.ctx.new_params['GbndRnge'][-1] + self.ctx.act_var['delta']*first

                self.ctx.calc_inputs.yres.gw.parameters = Dict(dict=self.ctx.new_params)

                self.ctx.param_vals.append(self.ctx.new_params['GbndRnge'][-1])

            elif self.ctx.act_var['var'] == 'kpoints': #meshes are different, so I need to do YamboWorkflow from scf (scratch).


                self.ctx.calc_inputs.scf.kpoints = KpointsData()
                self.ctx.calc_inputs.scf.kpoints.set_cell(self.ctx.calc_inputs.scf.pw.structure.cell)
                self.ctx.calc_inputs.scf.kpoints.set_kpoints_mesh_from_density(1/(self.ctx.act_var['delta']*i*first+1+self.ctx.act_var['delta']* \
                                                                                self.ctx.act_var['steps']*(self.ctx.k_last_dist-1)+(self.ctx.act_var['starting_mesh_density']-1)), force_parity=True)
                self.ctx.calc_inputs.nscf.kpoints = self.ctx.calc_inputs.scf.kpoints
                self.report('Mesh used: {} \nfrom density: {}'.format(self.ctx.calc_inputs.kpoints.get_kpoints_mesh(),2*i+1+6*(self.ctx.k_last_dist-1)))

                try:
                    del self.ctx.calc_inputs.parent_folder  #I need to start from scratch...
                except:
                    pass

                self.ctx.param_vals.append(self.ctx.calc_inputs.nscf.kpoints.get_kpoints_mesh()[0])


            else: #"scalar" quantity

                self.ctx.new_params = self.ctx.calc_inputs.yres.gw.parameters.get_dict()
                self.ctx.new_params[str(self.ctx.act_var['var'])] = self.ctx.new_params[str(self.ctx.act_var['var'])] + self.ctx.act_var['delta']*first

                self.ctx.calc_inputs.yres.gw.parameters = Dict(dict=self.ctx.new_params)

                self.ctx.param_vals.append(self.ctx.new_params[str(self.ctx.act_var['var'])])

            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i+1)] = future        #va cambiata eh!!! o forse no...forse basta mettere future
            self.ctx.act_var['wfl_pk'] = future.pk

        return ToContext(calc) #questo aspetta tutti i calcoli


    def conv_eval(self):

        self.ctx.first_calc = False
        self.report('Convergence evaluation')

        if self.ctx.act_var['var'] == 'kpoints':
            self.ctx.k_last_dist +=1


        try:
            converged, gaps = convergence_evaluation(self.ctx.act_var,take_gw_gap(self.ctx.act_var)) #redundancy..

            for i in range(self.ctx.act_var['steps']):

                self.ctx.all_calcs.append([self.ctx.act_var['var'],self.ctx.act_var['delta'],self.ctx.act_var['steps'], \
                                        self.ctx.act_var['conv_thr'],self.ctx.act_var['conv_window'], self.ctx.act_var['max_restarts'],  self.ctx.act_var['iter'], \
                                        len(load_node(self.ctx.act_var['wfl_pk']).caller.called)-self.ctx.act_var['steps']+i, \
                                        self.ctx.param_vals[i], gaps[i,1], int(gaps[i,2]), str(converged)]) #tracking the whole iterations and gaps

                self.ctx.conv_var.append([self.ctx.act_var['var'],self.ctx.act_var['delta'],self.ctx.act_var['steps'], \
                                        self.ctx.act_var['conv_thr'],self.ctx.act_var['conv_window'], self.ctx.act_var['max_restarts'],  self.ctx.act_var['iter'], \
                                        len(load_node(self.ctx.act_var['wfl_pk']).caller.called)-self.ctx.act_var['steps']+i, \
                                        self.ctx.param_vals[i], gaps[i,1], int(gaps[i,2]), str(converged)]) #tracking the whole iterations and gaps
            if converged:

                self.ctx.converged = True

                #taking as starting point just the first of the convergence window...
                last_ok_pk, oversteps = last_conv_calc_recovering(self.ctx.act_var,gaps[-1,1],'gap')
                self.report('oversteps:{}'.format(oversteps-1))
                last_ok = load_node(last_ok_pk)
                self.ctx.calc_inputs.yres.gw.parameters = last_ok.get_builder_restart().yres.gw['parameters'] #valutare utilizzo builder restart nel loop!!
                self.ctx.calc_inputs.scf.kpoints = last_ok.get_builder_restart().scf.kpoints
                self.ctx.calc_inputs.parent_folder = last_ok.outputs.yambo_calc_folder

                self.ctx.conv_var = self.ctx.conv_var[:-(oversteps-1)]

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

        self.ctx.act_var['iter']  += 1


    def report_wf(self): #mancano le unita'

        self.report('Final step. The workflow now will collect some info about the calculations in the "calc_info" output node ')

        #self.ctx.conv_var = (list(self.ctx.act_var.keys())+['calc_number','params_vals','gap']).append(self.ctx.conv_var)

        self.report('Converged variables: {}'.format(self.ctx.conv_var))

        converged_var = List(list=self.ctx.conv_var).store()
        all_var = List(list=self.ctx.all_calcs).store()
        self.out('conv_info', converged_var)
        self.out('all_calcs_info', all_var)

if __name__ == "__main__":
    pass
