# -*- coding: utf-8 -*-
from __future__ import absolute_import

from aiida.orm import RemoteData,BandsData
from aiida.orm import Dict,Int

from aiida.engine import WorkChain, while_, if_
from aiida.engine import ToContext

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.common.types import ElectronicType, SpinType

from aiida_yambo.utils.common_helpers import *
from aiida_yambo.workflows.yamborestart import YamboRestart

from aiida_yambo.utils.defaults.create_defaults import *
from aiida_yambo.workflows.utils.helpers_yambowf import *
from aiida.plugins import DataFactory
LegacyUpfData = DataFactory('upf')

from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

class YamboWorkflow(ProtocolMixin, WorkChain):

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
                            exclude = ['parent_folder'])

        spec.expose_inputs(PwBaseWorkChain, namespace='nscf', namespace_options={'required': True}, 
                            exclude = ['parent_folder'])

        spec.expose_inputs(YamboRestart, namespace='yres', namespace_options={'required': False}, 
                            exclude = ['parent_folder'])

        spec.input("additional_parsing", valid_type=List, required = False,
                    help = 'list of additional quantities to be parsed: gap, homo, lumo, or used defined quantities -with names-[k1,k2,b1,b2], [k1,b1]...')
        
        spec.input("parent_folder", valid_type=RemoteData, required = False,
                    help = 'scf, nscf or yambo remote folder')
  

##################################### OUTLINE ####################################

        spec.outline(cls.validate_parameters,
                    cls.start_workflow,
                    while_(cls.can_continue)(
                           cls.perform_next,
                    ),
                    if_(cls.post_processing_needed)(
                        cls.ypp_action,
                    ),
                    cls.report_wf,)

##################################################################################

        spec.expose_outputs(YamboRestart)
        
        spec.output('output_ywfl_parameters', valid_type = Dict, required = False)
        spec.output('nscf_mapping', valid_type = Dict, required = False)
        
        spec.output('scissor', valid_type = List, required = False)
        spec.output('band_structure_GW', valid_type = BandsData, required = False)
        spec.output('band_structure_DFT', valid_type = BandsData, required = False)

        spec.exit_code(300, 'ERROR_WORKCHAIN_FAILED',
                             message='The workchain failed with an unrecoverable error.')
    
    @classmethod
    def get_protocol_filepath(cls):
        """Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from aiida_yambo.workflows.protocols import yambo as yamboworkflow_protocols
        return files(yamboworkflow_protocols) / 'yamboworkflow.yaml'
    
    @classmethod
    def get_builder_from_protocol(
        cls,
        pw_code,
        preprocessing_code,
        code,
        protocol_qe='fast',
        protocol='GW_fast',
        structure=None,
        overrides=None,
        parent_folder=None,
        electronic_type=ElectronicType.INSULATOR,
        spin_type=SpinType.NONE,
        initial_magnetic_moments=None,
        **_
    ):
        """Return a builder prepopulated with inputs selected according to the chosen protocol.
        :return: a process builder instance with all inputs defined ready for launch.
        """
        from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

        if isinstance(code, str):
            
            preprocessing_code = orm.load_code(preprocessing_code)
            code = orm.load_code(code)

        if electronic_type not in [ElectronicType.METAL, ElectronicType.INSULATOR]:
            raise NotImplementedError(f'electronic type `{electronic_type}` is not supported.')

        if spin_type not in [SpinType.NONE, SpinType.COLLINEAR]:
            raise NotImplementedError(f'spin type `{spin_type}` is not supported.')

        inputs = cls.get_protocol_inputs(protocol, overrides={})

        meta_parameters = inputs.pop('meta_parameters',{})
        
        builder = cls.get_builder()

        overrides_scf = overrides.pop('scf',{})
        overrides_nscf = overrides.pop('nscf',{})
        overrides_yres = overrides.pop('yres',{})

        for override in [overrides_scf,overrides_nscf]:
            override['clean_workdir'] = override.pop('clean_workdir',False)
        
        overrides_nscf['pw'] = overrides_nscf.pop('pw',{'parameters':{}})
        overrides_nscf['pw']['parameters']['CONTROL'] = overrides_nscf['pw']['parameters'].pop('CONTROL',{'calculation':'nscf'})

        try:
            pw_parent = find_pw_parent(take_calc_from_remote(parent_folder))
            PW_cutoff = pw_parent.inputs.parameters.get_dict()['SYSTEM']['ecutwfc']
            nelectrons = int(pw_parent.outputs.output_parameters.get_dict()['number_of_electrons'])
        except:
            nelectrons, PW_cutoff = periodical(structure.get_ase())
            overrides_yres['nelectrons'] = nelectrons
            overrides_yres['PW_cutoff'] = PW_cutoff

        #########SCF and NSCF PROTOCOLS 
        builder.scf = PwBaseWorkChain.get_builder_from_protocol(
                pw_code,
                structure,
                protocol=protocol_qe,
                overrides=overrides_scf,
                electronic_type=electronic_type,
                spin_type=spin_type,
                initial_magnetic_moments=initial_magnetic_moments,
                )

        builder.nscf = PwBaseWorkChain.get_builder_from_protocol(
                pw_code,
                structure,
                protocol=protocol_qe,
                overrides=overrides_nscf,
                electronic_type=electronic_type,
                spin_type=spin_type,
                initial_magnetic_moments=initial_magnetic_moments,
                )
        
        nelectrons = 0
        for site in builder.nscf['pw']['structure'].sites:
            nelectrons += builder.nscf['pw']['pseudos'][site.kind_name].z_valence
        
        overrides_yres['nelectrons'] = nelectrons
        overrides_yres['PW_cutoff'] = builder.nscf['pw']['parameters'].get_dict()['SYSTEM']['ecutwfc']

        #########YAMBO PROTOCOL, with or without parent folder.
        if not parent_folder: 
            parent_folder = 'YWFL_scratch'
        else:
            builder.parent_folder = parent_folder
            parent_folder = 'YWFL_super_parent'


        builder.yres = YamboRestart.get_builder_from_protocol(
                preprocessing_code=preprocessing_code,
                code=code,
                protocol=protocol,
                parent_folder=parent_folder,
                overrides=overrides_yres,
            )

        if 'BndsRnXp' in builder.yres['yambo']['parameters'].get_dict()['variables'].keys():
            yambo_bandsX = builder.yres['yambo']['parameters'].get_dict()['variables']['BndsRnXp'][0][-1]
        else: 
            yambo_bandsX = 0 
        
        if 'GbndRnge' in builder.yres['yambo']['parameters'].get_dict()['variables'].keys():
            yambo_bandsSc = builder.yres['yambo']['parameters'].get_dict()['variables']['GbndRnge'][0][-1]
        else: 
            yambo_bandsSc = 0 
        
        gwbands = max(yambo_bandsX,yambo_bandsSc)

        parameters_nscf = builder.nscf['pw']['parameters'].get_dict()
        parameters_nscf['SYSTEM']['nbnd'] = max(parameters_nscf['SYSTEM'].pop('nbnd',0),gwbands)
        builder.nscf['pw']['parameters'] = Dict(dict = parameters_nscf)
        # pylint: enable=no-member

        return builder


    def validate_parameters(self):

        self.ctx.yambo_inputs = self.exposed_inputs(YamboRestart, 'yres')        
        self.report(self.ctx.yambo_inputs.yambo.parameters.get_dict())
        #quantumespresso common inputs
        self.ctx.scf_inputs = self.exposed_inputs(PwBaseWorkChain, 'scf')
        self.ctx.nscf_inputs = self.exposed_inputs(PwBaseWorkChain, 'nscf')
        
        #quantumespresso input parameters check from parents, if any.
        scf_params, nscf_params, redo_nscf, gwbands, messages = quantumespresso_input_validator(self.inputs,)
        if scf_params: self.ctx.scf_inputs.pw.parameters = scf_params
        if nscf_params: self.ctx.nscf_inputs.pw.parameters = nscf_params
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
            
            if parent.outputs.remote_folder.is_empty: 
                for i in range(2):
                    try:
                        parent = find_pw_parent(parent)
                        if parent.outputs.remote_folder.is_empty and i == 1: continue
                    except:
                        break
                    
            if parent.outputs.remote_folder.is_empty: raise

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
    
    def post_processing_needed(self):
        return False

    def ypp_action(self):
        pass

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

                if 'band_structure' in self.inputs.additional_parsing.get_list(): #in the future, also needed support for mergeqp, multiple calculations.
                    try:
                        b = QP_bands_interface(node=Int(self.ctx.calc.called[0].pk), mapping = Dict(dict = mapping))
                        self.report('electronic band structure computed by interpolation')
                        for k,v in b.items():
                            self.out(k, v)
                    except:
                        self.report('fail in the interpolation of the band structure')

            self.out_many(self.exposed_outputs(calc,YamboRestart))
            self.report("workflow completed successfully")
        else:
            self.report("workflow NOT completed successfully")
            return self.exit_codes.ERROR_WORKCHAIN_FAILED