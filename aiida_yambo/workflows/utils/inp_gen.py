# -*- coding: utf-8 -*-
"""Helper functions."""
from __future__ import absolute_import
import numpy as np
from collections.abc import Mapping

from aiida.orm import Dict, Str, Int
from aiida.plugins import CalculationFactory, DataFactory

from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

from aiida_yambo.calculations.gw import YamboCalculation


'''
1- with these functions, we do not need to define Dict or AiiDA Data...
that are immutable...
2 - the namespace maybe is possibly automatically detected when you specify the calculation/workchain... try to look in qe prepare_process_inputs...
3 - moreover, the number of inputs has to be determnined automatically, so that I have not to include it by hand
'''

def generate_pw_inputs(structure, code, pseudo_family, parameters, kpoints, metadata, \
                       exposed = False, parent_folder = None):

    PwCalculation = CalculationFactory('quantumespresso.pw')

    if not exposed:

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

        inputs = prepare_process_inputs(PwCalculation, inputs)

        return inputs


    else:

        ''' generation of inputs for exposed inputs such in the PwBaseWorkChain'''

        inputs ={'pw':{'metadata':{'options':{}}}}


        inputs['kpoints'] = kpoints

        #exposed  inputs:

        inputs['pw']['code'] = code
        inputs['pw']['structure'] = structure
        inputs['pw']['parameters'] = parameters
        inputs['pw']['pseudos'] = validate_and_prepare_pseudos_inputs(
            structure, pseudo_family = Str(pseudo_family))
        inputs['pw']['metadata'] =  metadata
        try:
            inputs['pw']['parent_folder'] = parent_folder.outputs.remote_folder
        except:
            pass

        from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
        inputs = prepare_process_inputs(PwBaseWorkChain, inputs) #fundamental: builds the expose_inputs...

        return inputs


def generate_yambo_inputs(metadata, preprocessing_code, precode_parameters, code, \
                        parameters, parent_folder, settings, max_restarts, exposed = False):

    #YamboCalculation = CalculationFactory('quantumespresso.pw')

    if not exposed:

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

        inputs = prepare_process_inputs(YamboCalculation, inputs)

        return inputs

    else:

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
        inputs['gw']['parent_folder'] = parent_folder

        from aiida_yambo.workflows.yamborestart_new import YamboRestartWf
        inputs = prepare_process_inputs(YamboRestartWf, inputs)

        return inputs
