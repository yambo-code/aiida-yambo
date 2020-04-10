# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import cmath

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
except:
    pass

################################################################################
'''
PAR_def_mode= "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")
'''
################################################################################
def fix_parallelism(inputs):
    update_dict(inputs.parameters, 'PAR_def_mode', 'balanced')
    return inputs.metadata.options

def fix_memory(inputs):
    update_dict(inputs.parameters, 'PAR_def_mode', 'memory')
    #inputs.metadata.options['mpi']=inputs.metadata.options['mpi']//2
    #inputs.metadata.options['openMP']=inputs.metadata.options['openMP']*2
    return inputs.metadata.options

def fix_time(inputs,restart):
    inputs.metadata.options['max_wallclock_seconds'] = \
                            int(inputs.metadata.options['max_wallclock_seconds']*1.3*restart)

    if inputs.metadata.options['max_wallclock_seconds'] > max_walltime.value:
        inputs.metadata.options['max_wallclock_seconds'] = max_walltime.value

    return inputs.metadata.options
