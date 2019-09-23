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

    for i in range(1, window):
        yambo_calc = workflows[-i].called[-1].called[-1]
        gap[i] = yambo_calc.outputs.array_qp.get_array('Eo')[0]+ \
                 yambo_calc.outputs.array_qp.get_array('E_minus_Eo')[0]

    if (abs(gap[-1]-gap[i]) for i in range(1,window)) > thr:
        return False
    else:
        return True

    return conv
'''
def fit_eval(thr, fit_type, calculations):

    if fit_type == '1/x':
        def f(a,b,c)
    elif fit_type == 'e^-x':
        def f(a,b,c)
        gggggg
'''
