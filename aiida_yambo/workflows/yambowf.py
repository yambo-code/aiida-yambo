# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import itertools

from aiida.orm import RemoteData,StructureData,KpointsData,UpfData
from aiida.orm import Dict,Str,Code

from aiida.engine import WorkChain, while_, append_
from aiida.engine import ToContext
from aiida.engine import submit

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs

from aiida_yambo.utils.common_helpers import *
from aiida_yambo.workflows.yamborestart import YamboRestart

from aiida_yambo.utils.defaults.create_defaults import *
from aiida_yambo.workflows.utils.helpers_yambowf import *
from aiida.plugins import DataFactory
LegacyUpfData = DataFactory('upf')


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
                            exclude = ['parent_folder', 'pw.parameters', 'pw.code','pw.structure'])

        spec.expose_inputs(PwBaseWorkChain, namespace='nscf', namespace_options={'required': True}, 
                            exclude = ['parent_folder', 'pw.parameters', 'pw.pseudos','pw.code','pw.structure'])

        spec.expose_inputs(YamboRestart, namespace='yres', namespace_options={'required': True}, 
                            exclude = ['parent_folder'])

        spec.input("additional_parsing", valid_type=List, required= False,
                    help = 'list of additional quantities to be parsed: gap, homo, lumo, or used defined quantities -with names-[k1,k2,b1,b2], [k1,b1]...')
        
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
        
        spec.output('output_ywfl_parameters', valid_type = Dict, required = False)
        spec.output('nscf_mapping', valid_type = Dict, required = False)

        spec.exit_code(300, 'ERROR_WORKCHAIN_FAILED',
                             message='The workchain failed with an unrecoverable error.')
    
    def validate_parameters(self):

        self.ctx.yambo_inputs = self.exposed_inputs(YamboRestart, 'yres')        

        #quantumespresso common inputs
        self.ctx.scf_inputs = self.exposed_inputs(PwBaseWorkChain, 'scf')
        self.ctx.nscf_inputs = self.exposed_inputs(PwBaseWorkChain, 'nscf')

        self.ctx.scf_inputs.pw.structure = self.inputs.structure
        self.ctx.nscf_inputs.pw.structure = self.inputs.structure

        #self.ctx.scf_inputs.pw.pseudos = self.inputs.pseudos
        self.ctx.nscf_inputs.pw.pseudos = self.ctx.scf_inputs.pw.pseudos

        self.ctx.scf_inputs.pw.code = self.inputs.pw_code
        self.ctx.nscf_inputs.pw.code = self.inputs.pw_code
        
        #quantumespresso input parameters
        scf_params, nscf_params, redo_nscf, gwbands, messages = quantumespresso_input_validator(self.inputs,)
        self.ctx.scf_inputs.pw.parameters = scf_params
        self.ctx.nscf_inputs.pw.parameters = nscf_params
        self.ctx.redo_nscf = redo_nscf
        self.ctx.gwbands = gwbands
        for i in messages:
            self.report(i)
        
    def start_workflow(self):
        """Initialize the workflow, set the parent calculation

        This function sets the parent, and its type
        there is no submission done here, only setting up the neccessary inputs the workchain needs in the next
        steps to decide what are the subsequent steps"""

        try:

            parent = take_calc_from_remote(self.inputs.parent_folder)
            if parent.process_type=='aiida.workflows:quantumespresso.pw.base':
                parent = parent.called[0]

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
  
        try:
            calc = self.ctx.calc
            if not calc.is_finished_ok:
                self.report("last calculation failed, exiting the workflow")
                return self.exit_codes.ERROR_WORKCHAIN_FAILED
        except:
            pass

        self.report('performing a {} calculation'.format(self.ctx.calc_to_do))

        if self.ctx.calc_to_do == 'scf':

            self.ctx.scf_inputs.metadata.call_link_label = 'scf'
            future = self.submit(PwBaseWorkChain, **self.ctx.scf_inputs)

            self.ctx.calc_to_do = 'nscf'

        elif self.ctx.calc_to_do == 'nscf':

            try:
                self.ctx.nscf_inputs.pw.parent_folder = self.ctx.calc.called[0].outputs.remote_folder
            except:
                self.ctx.nscf_inputs.pw.parent_folder = self.ctx.calc.outputs.remote_folder
            
            self.ctx.nscf_inputs.metadata.call_link_label = 'nscf'  
            future = self.submit(PwBaseWorkChain, **self.ctx.nscf_inputs)

            self.ctx.calc_to_do = 'yambo'

        elif self.ctx.calc_to_do == 'yambo':

            try:
                self.ctx.yambo_inputs['parent_folder'] = self.ctx.calc.called[0].outputs.remote_folder
            except:
                self.ctx.yambo_inputs['parent_folder'] = self.ctx.calc.outputs.remote_folder

            if hasattr(self.inputs, 'additional_parsing'):
                self.report('updating yambo parameters to parse more results')
                mapping, yambo_parameters = add_corrections(self.ctx.yambo_inputs, self.inputs.additional_parsing.get_list())
                self.ctx.yambo_inputs.yambo.parameters = yambo_parameters

            self.ctx.yambo_inputs.metadata.call_link_label = 'yambo'
            future = self.submit(YamboRestart, **self.ctx.yambo_inputs)

            self.ctx.calc_to_do = 'the workflow is finished'

        return ToContext(calc = future)

    def report_wf(self):

        self.report('Final step.')

        calc = self.ctx.calc
        if calc.is_finished_ok:
            if hasattr(self.inputs, 'additional_parsing'):
                self.report('parsing additional quantities')
                mapping, yambo_parameters = add_corrections(self.ctx.yambo_inputs, self.inputs.additional_parsing.get_list())
                parsed = additional_parsed(calc, self.inputs.additional_parsing.get_list(), mapping)
                self.out('nscf_mapping', store_Dict(mapping))
                self.out('output_ywfl_parameters', store_Dict(parsed))

            self.out_many(self.exposed_outputs(calc,YamboRestart))
            self.report("workflow completed successfully")

        else:
            self.report("workflow NOT completed successfully")
            return self.exit_codes.ERROR_WORKCHAIN_FAILED