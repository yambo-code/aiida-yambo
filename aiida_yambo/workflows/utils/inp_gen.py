# -*- coding: utf-8 -*-
"""Helper functions."""
from __future__ import absolute_import
import numpy as np
from collections.abc import Mapping

from aiida.orm import Dict, Str, Int, RemoteData
from aiida.plugins import CalculationFactory, DataFactory, WorkflowFactory

from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.utils.mapping import prepare_process_inputs


'''
1- with these functions, we do not need to define Dict or AiiDA Data...
that are immutable...
2 - the namespace maybe is possibly automatically detected when you specify the calculation/workchain... try to look in qe prepare_process_inputs...
3 - moreover, the number of inputs has to be determnined automatically, so that I have not to include it by hand
'''
#YamboRestart = WorkflowFactory('yambo.yambo.yamborestart')

def generate_pw_inputs(structure, code, pseudo_family, parameters, kpoints, metadata, \
                        parent_folder = None , type_calc = 'PwCalculation'):



    if type_calc == 'PwCalculation':

        """Construct a builder for the `PwCalculation` class and populate its inputs.

	"""


        #inputs ={'metadata':{'options':{}}}
        inputs = {}

        inputs['kpoints'] = kpoints
        inputs['code'] = code
        inputs['structure'] = structure
        inputs['parameters'] = parameters
        inputs['pseudos'] = validate_and_prepare_pseudos_inputs(
            structure, pseudo_family = Str(pseudo_family))
        inputs['metadata'] =  metadata
        try:
            inputs['parent_folder'] = parent_folder.outputs.remote_folder
        except:
            pass

        PwCalculation = CalculationFactory('quantumespresso.pw')
        inputs = prepare_process_inputs(PwCalculation, inputs)

        return inputs


    elif type_calc == 'PwBaseWorkChain':

        ''' generation of inputs for type_calc inputs such in the PwBaseWorkChain'''

        inputs ={'pw':{'metadata':{'options':{}}}}


        inputs['kpoints'] = kpoints

        #type_calc  inputs:

        inputs['pw']['code'] = code
        inputs['pw']['structure'] = structure
        inputs['pw']['parameters'] = parameters
        inputs['pw']['pseudos'] = validate_and_prepare_pseudos_inputs(
            structure, pseudo_family = Str(pseudo_family))
        inputs['pw']['metadata'] =  metadata
        try:
            inputs['parent_folder'] = parent_folder.outputs.remote_folder
        except:
            pass

        from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
        inputs = prepare_process_inputs(PwBaseWorkChain, inputs) #fundamental: builds the expose_inputs...

        return inputs

    elif type_calc == 'scf in YamboWorkflow':

        ''' generation of inputs for type_calc inputs such in the PwBaseWorkChain'''

        inputs = {'scf':{'pw':{'metadata':{'options':{}}}}}


        inputs['scf']['kpoints'] = kpoints

        #type_calc  inputs:

        inputs['scf']['pw']['code'] = code
        inputs['scf']['pw']['structure'] = structure
        inputs['scf']['pw']['parameters'] = parameters
        inputs['scf']['pw']['pseudos'] = validate_and_prepare_pseudos_inputs(
            structure, pseudo_family = Str(pseudo_family))
        inputs['scf']['pw']['metadata'] =  metadata

        from aiida_yambo.workflows.yambowf import YamboWorkflow
        inputs = prepare_process_inputs(YamboWorkflow, inputs)

        return inputs

    elif type_calc == 'nscf in YamboWorkflow':

        ''' generation of inputs for type_calc inputs such in the PwBaseWorkChain'''

        inputs = {'nscf':{'pw':{'metadata':{'options':{}}}}}


        inputs['nscf']['kpoints'] = kpoints

        #type_calc  inputs:

        inputs['nscf']['pw']['code'] = code
        inputs['nscf']['pw']['structure'] = structure
        inputs['nscf']['pw']['parameters'] = parameters
        inputs['nscf']['pw']['pseudos'] = validate_and_prepare_pseudos_inputs(
            structure, pseudo_family = Str(pseudo_family))
        inputs['nscf']['pw']['metadata'] =  metadata


        from aiida_yambo.workflows.yambowf import YamboWorkflow
        inputs = prepare_process_inputs(YamboWorkflow, inputs)

        return inputs


def generate_yambo_inputs(metadata, preprocessing_code, precode_parameters, code, \
                        parameters, settings, parent_folder = None, max_restarts = 5, type_calc = 'YamboCalculation'):

    '''This is a very long if else... there should be a way to
       automatically decide and store these values
    '''

    if type_calc == 'YamboCalculation':

        """Construct a builder for the `YamboCalculation` class and populate its inputs.

	"""


        inputs = {}

        inputs['settings'] = settings  #True if just p2y calculation
        inputs['precode_parameters']= precode_parameters #options for p2y...
        inputs['preprocessing_code'] = preprocessing_code #p2y
        inputs['code'] = code  #yambo executable

        inputs['parameters'] = parameters
        inputs['metadata'] =  metadata
        inputs['parent_folder'] = parent_folder

        from aiida_yambo.calculations.gw import YamboCalculation
        inputs = prepare_process_inputs(YamboCalculation, inputs)

        return inputs

    elif type_calc == 'YamboRestartWf':

        """Construct a builder for the `YamboRestart` class and populate its inputs.

	"""


        inputs = {'gw':{'metadata':{'options':{}}}}

        inputs['max_restarts'] = Int(max_restarts)

        inputs['gw']['settings'] = settings  #True if just p2y calculation
        inputs['gw']['precode_parameters'] = precode_parameters #options for p2y...
        inputs['gw']['preprocessing_code'] = preprocessing_code #p2y
        inputs['gw']['code'] = code  #yambo executable

        inputs['gw']['parameters'] = parameters
        inputs['gw']['metadata'] =  metadata
        inputs['parent_folder'] = parent_folder

        from aiida_yambo.workflows.yamborestart import YamboRestartWf
        inputs = prepare_process_inputs(YamboRestartWf, inputs)

        return inputs

    elif type_calc == 'YamboWorkflow':

        """Construct a builder for the `YamboRestart` class and populate its inputs.

	"""

        inputs = {'yres':{'gw':{'metadata':{'options':{}}}}}

        inputs['yres']['max_restarts'] = Int(max_restarts)

        inputs['yres']['gw']['settings'] = settings  #True if just p2y calculation
        inputs['yres']['gw']['precode_parameters'] = precode_parameters #options for p2y...
        inputs['yres']['gw']['preprocessing_code'] = preprocessing_code #p2y
        inputs['yres']['gw']['code'] = code  #yambo executable

        inputs['yres']['gw']['parameters'] = parameters
        inputs['yres']['gw']['metadata'] =  metadata

        try:
            inputs['parent_folder'] = parent_folder.outputs.remote_folder
        except:
            pass

        from aiida_yambo.workflows.yambowf import YamboWorkflow
        inputs = prepare_process_inputs(YamboWorkflow, inputs)

        return inputs

def generate_yambo_convergence_inputs(yambo,  var_to_conv, fit_options, scf, nscf):

    wfl_dict = {**scf, **nscf, **yambo}

    inputs = {'ywfl': wfl_dict}

    inputs['kpoints'] = inputs['ywfl']['scf'].pop('kpoints')
    inputs['kpoints'] = inputs['ywfl']['scf'].pop('kpoints')

    inputs['var_to_conv'] = Dict(dict=var_to_conv)
    inputs['fit_options'] = Dict(dict=fit_options)

    from aiida_yambo.workflows.yamboconv import YamboConvergence
    inputs = prepare_process_inputs(YamboConvergence, inputs)

    return inputs



################################################################################
################################################################################


#for YamboConvergence:
def get_updated_mesh(starting_mesh,i,delta):

    mesh, shift = starting_mesh.get_kpoints_mesh()

    for j in range(0,3):
        if mesh[j] != 1:
            mesh[j] = mesh[j]*(delta+i)


    new_mesh  = DataFactory('array.kpoints').set_kpoints_mesh(mesh, shift)

    return new_mesh



################################################################################
################################################################################









def recursive_yambo_inputs(metadata, preprocessing_code, precode_parameters, code, \
                        parameters, settings, parent_folder = None, max_restarts = 5, type_calc = 'YamboCalculation'):

    '''This is a very long if else... there should be a way to
       automatically decide and store these values
    '''

    if type_calc == 'YamboCalculation':

        """Construct a builder for the `YamboCalculation` class and populate its inputs.

	"""
        inputs = {}

        inputs['settings'] = settings  #True if just p2y calculation
        inputs['precode_parameters']= precode_parameters #options for p2y...
        inputs['preprocessing_code'] = preprocessing_code #p2y
        inputs['code'] = code  #yambo executable

        inputs['parameters'] = parameters
        inputs['metadata'] =  metadata
        inputs['parent_folder'] = parent_folder

        from aiida_yambo.calculations.gw import YamboCalculation
        inputs = prepare_process_inputs(YamboCalculation, inputs)

        return inputs

    elif type_calc == 'YamboRestartWf':

        """Construct a builder for the `YamboRestart` class and populate its inputs.

	"""
        inputs = {'gw': recursive_yambo_inputs(metadata, preprocessing_code, precode_parameters, code, \
                                parameters, settings, parent_folder, max_restarts, type_calc = 'YamboCalculation').get_dict()}
        inputs['parent_folder'] = inputs['gw'].pop('parent_folder')
        from aiida_yambo.workflows.yamborestart import YamboRestartWf
        inputs = prepare_process_inputs(YamboRestartWf, inputs)
        return inputs
