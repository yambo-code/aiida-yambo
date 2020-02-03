# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools
import traceback

#if aiida_calcs:
from aiida.orm import Dict, Str, KpointsData, RemoteData, List, load_node

from aiida.engine import WorkChain, while_ , if_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_yambo.workflows.utils.helpers_workflow import *

class YamboMassive(WorkChain):

    """This workflow will perform yambo calculation for a set of parameters, without doing any convergence evaluation.
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

        spec.input("parameters", valid_type=List, required=True, \
                    help = 'variables to converge, range, steps, and max restarts')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    if_(cls.p2y_needed)(
                    cls.do_p2y,
                    cls.prepare_calculations,
                    ),
                    cls.massive_calcs,
                    if_(cls.post_processing)(
                    cls.final_analysis
                    ),
                    cls.report_wf,
                    )

##################################################################################

        spec.output('conv_info', valid_type = List, help='list with convergence path')
        spec.output('all_calcs_info', valid_type = List, help='all calculations')


    def start_workflow(self):
        """Initialize the workflow"""

        self.ctx.calc_inputs = self.exposed_inputs(YamboWorkflow, 'ywfl')
        self.ctx.calc_inputs.scf.kpoints = self.inputs.kpoints
        self.ctx.calc_inputs.nscf.kpoints = self.inputs.kpoints

        self.ctx.workflow_manager = workflow_manager(self.inputs.var_to_conv)
        self.ctx.workflow_manager.global_step = 0
        self.ctx.workflow_manager.fully_converged = False

        self.ctx.calc_manager = calc_manager(self.ctx.workflow_manager.true_iter.pop())
        self.ctx.calc_manager._type = 'yambo'
        self.ctx.calc_manager.iter  = 1
        self.ctx.calc_manager.converged = False

        self.ctx.workflow_manager.first_calc = True

        self.report("workflow initilization step completed, the first variable will be {}.".format(self.ctx.calc_manager.var))

    def next_step(self):
        """This function will submit the next step"""



            future = self.submit(YamboWorkflow, **self.ctx.calc_inputs)
            calc[str(i)] = future
            self.ctx.calc_manager.wfl_pk = future.pk

        return ToContext(calc)


    def post_processing(self):
        pass

    def final_analysis(self):
        pass

    def report_wf(self):

        self.report('Final step. It is {} that the workflow was successful'.format(str(self.ctx.workflow_manager.fully_converged)))
        all_var = List(list=self.ctx.workflow_manager.absolute_story).store()
        converged_var = List(list=self.ctx.workflow_manager.conv_story).store()
        self.out('conv_info', converged_var)
        self.out('all_calcs_info', all_var)

    def p2y_needed(self):
        self.report('do we need a p2y??')
        try:
            self.ctx.calc_manager.set_parent(self.ctx.calc_inputs.parent_folder, self.inputs.parent_folder)
            parent_calc = find_parent()

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
        self.ctx.calc_manager.update_dict(self.ctx.calc_inputs.yres.gw.settings, 'INITIALISE', True)
        calc['p2y'] = self.submit(YamboWorkflow, **self.ctx.calc_inputs) #################run
        self.report('Submitted YamboWorkflow up to p2y, pk = {}'.format(calc['p2y'].pk))
        self.ctx.calc_manager.update_dict(self.ctx.calc_inputs.yres.gw.settings, 'INITIALISE', False)
        self.ctx.p2y = calc['p2y']
        return ToContext(calc)

    def prepare_calculations(self):
        self.report('setting the p2y calc as parent')
        self.ctx.calc_manager.set_parent(self.ctx.calc_inputs.parent_folder, self.ctx.p2y.outputs.yambo_calc_folder)

if __name__ == "__main__":
    pass
