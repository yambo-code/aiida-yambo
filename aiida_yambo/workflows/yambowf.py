# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import RemoteData
from aiida.orm import Dict

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain

from aiida_yambo.workflows.yamborestart import YamboRestartWf

class YamboWorkflow(WorkChain):

    """This workflow will perform yambo calculation on the top of scf+nscf or from scratch,
    invoking qe workchains.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """
        super(YamboWorkflow, cls).define(spec)

        spec.expose_inputs(PwBaseWorkChain, namespace='pw', \
                            namespace_options={'required': False}, exclude = 'parent_folder', \
                            help = 'needed if we start from scratch or scf')

        spec.expose_inputs(YamboRestartWf, namespace='gw', exclude = 'parent_folder')

        spec.input("parent_folder", valid_type=RemoteData, required=False, default = None)

        spec.input("nscf_extra_parameters", valid_type=Dict, required=False, default = None, \
                    help = 'extra parameters if we start from scratch, so the exposed inputs are for a scf calculation')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                     while_(cls.can_continue)(
                     cls.perform_next),
                     cls.report_wf,
                     )

##################################################################################

        spec.output('yambo_calc_folder', valid_type = RemoteData,
            help='The final yambo calculation remote folder.')

    def start_workflow(self):
        """Initialize the workflow, set the parent calculation

        This function sets the parent, and its type, including support for starting from a previos workchain,
        there is no submission done here, only setting up the neccessary inputs the workchain needs in the next
        steps to decide what are the subsequent steps"""

        try:

            with self.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder') as parent:

                if parent.process_type=='aiida.calculations:quantumespresso.pw' and parent.is_finished_ok:

                    if parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'scf':
                        self.ctx.calc_to_do = 'nscf'

                    elif parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'nscf':
                        self.ctx.calc_to_do = 'yambo'

                elif parent.process_type=='aiida.calculations:yambo.yambo':
                    self.ctx.calc_to_do = 'yambo'

                else:
                    self.ctx.previous_pw = False
                    self.ctx.calc_to_do = 'scf'
                    self.report('no valid input calculations, so we will start from scratch')
        except:

            self.report('no previous pw calculation found, \
                                we will start from scratch')
            self.ctx.calc_to_do = 'scf'

        self.report(" workflow initilization step completed.")

    def can_continue(self):

        """This function checks the status of the last calculation and determines what happens next, including a successful exit"""

        if self.ctx.calc_to_do != 'the workflow is finished':
            self.report('the workflow continues with a {} calculation'.format(self.ctx.calc_to_do))
            return True
        else:
            self.report('the workflow is finished')
            return False


    def perform_next(self):
        """This function  will submit the next step, depending on the information provided in the context

        The next step will be a yambo calculation if the provided inputs are a previous yambo/p2y run
        Will be a PW scf/nscf if the inputs do not provide the NSCF or previous yambo parent calculations"""

        self.report('performing a {} calculation'.format(self.ctx.calc_to_do))


        if self.ctx.calc_to_do == 'scf':

            self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'pw')

            from aiida_yambo.workflows.utils.inp_gen import generate_pw_inputs
            inputs = generate_pw_inputs(**self.ctx.pw_inputs, exposed = True)

            future = self.submit(PwBaseWorkChain, **inputs)

            self.ctx.calc_to_do = 'nscf'

        elif self.ctx.calc_to_do == 'nscf':

            self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'pw')

            try:
                self.ctx.pw_inputs = self.ctx.pw_inputs.update(self.inputs.nscf_extra_parameters)

            except:
                pass # for now...small support if no nscf parameters are given... bands from yambo inputs... and something like that

            from aiida_yambo.workflows.utils.inp_gen import generate_pw_inputs
            inputs = generate_pw_inputs(**self.ctx.pw_inputs, exposed = True)

            future = self.submit(PwBaseWorkChain, **inputs)

            self.ctx.calc_to_do = 'yambo'

        elif self.ctx.calc_to_do == 'yambo':

            self.ctx.yambo_inputs = self.exposed_inputs(YamboRestartWf, 'gw')

            from aiida_yambo.workflows.utils.inp_gen import generate_yambo_inputs
            inputs = generate_yambo_inputs(**self.ctx.pw_inputs, exposed = True)

            future = self.submit(YamboRestartWf, **inputs)

            self.ctx.calc_to_do = 'the workflow is finished'


        return ToContext(calc = future)


    def report_wf(self):

        self.report('Final step.')

        calc = self.ctx.calc
        self.report("workflow completed successfully: {}, last calculation was <{}>".format(calc.is_finished_ok, calc.pk))
        self.out('last_calc_folder', calc.outputs.last_calc_folder)


if __name__ == "__main__":
    pass
