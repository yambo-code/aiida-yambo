# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import RemoteData
from aiida.orm import Dict

from aiida.engine import WorkChain, while_, append_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain

from aiida_yambo.utils.common_helpers import *
from aiida_yambo.workflows.yamborestart import YamboRestart

class YamboWorkflow(WorkChain):

    """This workflow will perform yambo calculation on the top of scf+nscf or from scratch,
        using also the PwBaseWorkChain.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """

        super(YamboWorkflow, cls).define(spec)

        spec.expose_inputs(PwBaseWorkChain, namespace='scf', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])

        spec.expose_inputs(PwBaseWorkChain, namespace='nscf', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])

        spec.expose_inputs(YamboRestart, namespace='yres', namespace_options={'required': True}, \
                            exclude = ['parent_folder'])

        spec.input("parent_folder", valid_type=RemoteData, required= False,\
                    help = 'scf, nscf or yambo remote folder')

##################################### OUTLINE ####################################

        spec.outline(cls.start_workflow,
                    while_(cls.can_continue)(
                           cls.perform_next,
                    ),
                     cls.report_wf,)

##################################################################################

        spec.expose_outputs(YamboRestart)

        spec.exit_code(300, 'ERROR_WORKCHAIN_FAILED',
                             message='The workchain failed with an unrecoverable error.')

    def start_workflow(self):
        """Initialize the workflow, set the parent calculation

        This function sets the parent, and its type
        there is no submission done here, only setting up the neccessary inputs the workchain needs in the next
        steps to decide what are the subsequent steps"""

        try:

            parent = take_calc_from_remote(self.inputs.parent_folder)

            if parent.process_type=='aiida.calculations:quantumespresso.pw':

                if parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'scf' or parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'relax' or \
                parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'vc-relax':
                    self.ctx.calc_to_do = 'nscf'

                elif parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'nscf':
                    self.ctx.calc_to_do = 'yambo'

            elif parent.process_type=='aiida.calculations:yambo.yambo':
                self.ctx.calc_to_do = 'yambo'

            else:
                self.ctx.previous_pw = False
                self.ctx.calc_to_do = 'scf'
                self.report('no valid input calculations, so we will start from scratch')
            
            self.ctx.calc = parent

        except:

            self.report('no previous pw calculation found, we will start from scratch')
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

        
        try:
            calc = self.ctx.calc
            if not calc.is_finished_ok:
                self.report("last calculation failed, exiting the workflow")
                return self.exit_codes.ERROR_WORKCHAIN_FAILED
        except:
            pass
            
        if self.ctx.calc_to_do == 'scf':

            self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'scf')

            future = self.submit(PwBaseWorkChain, **self.ctx.pw_inputs)

            self.ctx.calc_to_do = 'nscf'

        elif self.ctx.calc_to_do == 'nscf':

            self.ctx.pw_inputs = self.exposed_inputs(PwBaseWorkChain, 'nscf')

            try:
                self.ctx.pw_inputs.pw.parent_folder = self.ctx.calc.called[0].outputs.remote_folder
            except:
                self.ctx.pw_inputs.pw.parent_folder = self.ctx.calc.outputs.remote_folder

            future = self.submit(PwBaseWorkChain, **self.ctx.pw_inputs)

            self.ctx.calc_to_do = 'yambo'

        elif self.ctx.calc_to_do == 'yambo':

            self.ctx.yambo_inputs = self.exposed_inputs(YamboRestart, 'yres')

            try:
                self.ctx.yambo_inputs['parent_folder'] = self.ctx.calc.called[0].outputs.remote_folder
            except:
                self.ctx.yambo_inputs['parent_folder'] = self.ctx.calc.outputs.remote_folder

            future = self.submit(YamboRestart, **self.ctx.yambo_inputs)

            self.ctx.calc_to_do = 'the workflow is finished'

        return ToContext(calc = future)

    def report_wf(self):

        self.report('Final step.')

        calc = self.ctx.calc
        if calc.is_finished_ok:
            self.report("workflow completed successfully")
            
            self.out_many(self.exposed_outputs(calc,YamboRestart))

        else:
            self.report("workflow NOT completed successfully")
            return self.exit_codes.ERROR_WORKCHAIN_FAILED