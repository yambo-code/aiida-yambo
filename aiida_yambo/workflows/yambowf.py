# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import RemoteData,StructureData,KpointsData
from aiida.orm import Dict,Str,Code

from aiida.engine import WorkChain, while_, append_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs

from aiida_yambo.utils.common_helpers import *
from aiida_yambo.workflows.yamborestart import YamboRestart

from aiida_yambo.workflows.utils.defaults.create_defaults import *

class YamboWorkflow(WorkChain):

    """This workflow will perform yambo calculation on the top of scf+nscf or from scratch,
        using also the PwBaseWorkChain.
    """
    pw_exclude = ['parent_folder', 'pw.parameters','pw.pseudos','pw.code','pw.structure', 'kpoints']

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        """

        super(YamboWorkflow, cls).define(spec)

        spec.expose_inputs(PwBaseWorkChain, namespace='scf', namespace_options={'required': True}, 
                            exclude = ['parent_folder', 'pw.parameters', 'pw.pseudos','pw.code','pw.structure'])

        spec.expose_inputs(PwBaseWorkChain, namespace='nscf', namespace_options={'required': True}, 
                            exclude = ['parent_folder', 'pw.parameters', 'pw.pseudos','pw.code','pw.structure'])

        spec.expose_inputs(YamboRestart, namespace='yres', namespace_options={'required': True}, 
                            exclude = ['parent_folder'])

        spec.input("parent_folder", valid_type=RemoteData, required= False,
                    help = 'scf, nscf or yambo remote folder')

        #DFT inputs, not required
        spec.input('scf_parameters', valid_type=Dict, required = False,
                    help = 'scf params')
        spec.input('nscf_parameters', valid_type=Dict, required = False,
                    help = 'nscf params')  

        #Both scf and nscf DFT inputs, required   
        spec.input('structure', valid_type=StructureData, required= True,
                    help = 'structure')
        spec.input('pseudo_family', valid_type=Str, required= True,
                    help = 'pseudo family')
        spec.input('pw_code', valid_type=Code, required= True,
                    help = 'code for pw part')

##################################### OUTLINE ####################################

        spec.outline(cls.validate_parameters,
                    cls.start_workflow,
                    while_(cls.can_continue)(
                           cls.perform_next,
                    ),
                     cls.report_wf,)

##################################################################################

        spec.expose_outputs(YamboRestart)

        spec.exit_code(300, 'ERROR_WORKCHAIN_FAILED',
                             message='The workchain failed with an unrecoverable error.')
    
    def validate_parameters(self):


        self.ctx.scf_inputs = self.exposed_inputs(PwBaseWorkChain, 'scf')
        self.ctx.nscf_inputs = self.exposed_inputs(PwBaseWorkChain, 'nscf')

        self.ctx.yambo_inputs = self.exposed_inputs(YamboRestart, 'yres')
        
        self.ctx.scf_inputs.pw.structure = self.inputs.structure
        self.ctx.nscf_inputs.pw.structure = self.inputs.structure

        self.ctx.scf_inputs.pw.pseudos = validate_and_prepare_pseudos_inputs(
                self.ctx.scf_inputs.pw.structure, pseudo_family = self.inputs.pseudo_family)
        self.ctx.nscf_inputs.pw.pseudos = self.ctx.scf_inputs.pw.pseudos

        self.ctx.scf_inputs.pw.code = self.inputs.pw_code
        self.ctx.nscf_inputs.pw.code = self.inputs.pw_code
        
        yambo_bandsX = self.ctx.yambo_inputs.yambo.parameters.get_dict().pop('BndsRnXp',[0])[-1]
        yambo_bandsSc = self.ctx.yambo_inputs.yambo.parameters.get_dict().pop('GbndRnge',[0])[-1]
        self.ctx.gwbands = max(yambo_bandsX,yambo_bandsSc)
        self.report('GW bands are: {} '.format(self.ctx.gwbands))
        scf_params, nscf_params = create_quantumespresso_inputs(self.ctx.scf_inputs.pw.structure, bands_gw = self.ctx.gwbands)


        if hasattr(self.inputs,'scf_parameters'):
            self.report('scf inputs found')  
            self.ctx.scf_inputs.pw.parameters =  self.inputs.scf_parameters
        else:
            self.report('scf inputs not found, setting defaults')
            scf_params['SYSTEM']['nbnd'] = int(scf_params['SYSTEM']['nbnd'])
            self.ctx.scf_inputs.pw.parameters =  Dict(dict=scf_params)
        
        self.ctx.redo_nscf = False
        if hasattr(self.inputs,'nscf_parameters'):
            self.report('nscf inputs found')  
            self.ctx.nscf_inputs.pw.parameters =  self.inputs.nscf_parameters
            if self.ctx.nscf_inputs.pw.parameters.get_dict()['SYSTEM']['nbnd'] < self.ctx.gwbands:
                self.ctx.redo_nscf = True
                self.report('setting nbnd of the nscf calculation to b = {}'.format(self.ctx.gwbands))
                nscf_params = self.ctx.nscf_inputs.pw.parameters.get_dict()
                nscf_params['SYSTEM']['nbnd'] = int(self.ctx.gwbands)
                self.ctx.nscf_inputs.pw.parameters = Dict(dict=nscf_params)
            
        else:
            self.report('nscf inputs not found, setting defaults')
            nscf_params['SYSTEM']['nbnd'] = int(nscf_params['SYSTEM']['nbnd'])
            self.ctx.nscf_inputs.pw.parameters =  Dict(dict=nscf_params)
        
        
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
                    self.ctx.redo_nscf = False

                elif parent.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'nscf':
                    if self.ctx.redo_nscf or parent.inputs.parameters.get_dict()['SYSTEM']['nbnd'] < self.ctx.gwbands:
                        parent = find_pw_parent(parent, calc_type = ['scf'])
                        self.report('Recomputing NSCF step, not enough bands. Starting from scf at pk < {} >'.format(parent.pk))
                        self.ctx.calc_to_do = 'nscf'
                        self.ctx.redo_nscf = False
                    else:
                        self.ctx.calc_to_do = 'yambo'

            elif parent.process_type=='aiida.calculations:yambo.yambo':
                    nbnd = find_pw_parent(parent, calc_type = ['nscf']).inputs.parameters.get_dict()['SYSTEM']['nbnd']
                    if self.ctx.redo_nscf or nbnd < self.ctx.gwbands:
                        parent = find_pw_parent(parent, calc_type = ['scf'])
                        self.report('Recomputing NSCF step, not enough bands. Starting from scf at pk < {} >'.format(parent.pk))
                        self.ctx.calc_to_do = 'nscf'
                        self.ctx.redo_nscf = False
                    else:
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

            future = self.submit(PwBaseWorkChain, **self.ctx.scf_inputs)

            self.ctx.calc_to_do = 'nscf'

        elif self.ctx.calc_to_do == 'nscf':

            try:
                self.ctx.nscf_inputs.pw.parent_folder = self.ctx.calc.called[0].outputs.remote_folder
            except:
                self.ctx.nscf_inputs.pw.parent_folder = self.ctx.calc.outputs.remote_folder

            future = self.submit(PwBaseWorkChain, **self.ctx.nscf_inputs)

            self.ctx.calc_to_do = 'yambo'

        elif self.ctx.calc_to_do == 'yambo':

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