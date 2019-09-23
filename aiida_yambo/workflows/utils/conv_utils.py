# -*- coding: utf-8 -*-
"""Helper functions."""
from __future__ import absolute_import
import numpy as np
from collections.abc import Mapping

from aiida.orm import Dict, Str
from aiida.plugins import CalculationFactory, DataFactory

from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.mapping import prepare_process_inputs

'''
convergence functions for gw convergences.
'''

def conv_eval(thr, window, workflows):

    yambo_calc = workflows.outputs.yambo_calc_folder.get_incoming() \
                .get_node_by_label['remote_folder']

    for i in range(1, window):
        gap[i] = yambo_calc[str(i)].outputs.array_qp.get_array('Eo')[0]+ \
                 yambo_calc[str(i)].outputs.array_qp.get_array('E_minus_Eo')[0]

    if (delta[i] for i in range(1,len(calculations))) > thr:
        conv = False
    else:
        conv = True

    return conv

def fit_eval(thr, fit_type, calculations):

    if fit_type == '1/x':
        #def f(a,b,c)
    elif fit_type == 'e^-x':
        #def f(a,b,c)
