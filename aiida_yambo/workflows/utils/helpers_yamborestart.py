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
    from aiida_yambo.utils.parallelism_finder import *
except:
    pass

################################################################################
'''
PAR_def_mode= "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")
'''
################################################################################
def fix_parallelism(options, failed_calc):

    what = ['bands','kpoints']
    bands, qp, last_qp, runlevels = find_gw_info(failed_calc)
    occupied, kpoints = take_filled_states(failed_calc), take_number_kpts(failed_calc)


    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_options = find_parallelism_qp(options['num_machines'], options['num_mpiprocs_per_machine'], \
                                                        options['num_cores_per_mpiproc'], bands, \
                                                        occupied, qp, kpoints,\
                                                        what, last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_options

def fix_memory(options, failed_calc):

    what = ['bands','kpoints']
    bands, qp, last_qp, runlevels = find_gw_info(failed_calc)
    occupied, kpoints = take_filled_states(failed_calc), take_number_kpts(failed_calc)

    if options['num_mpiprocs_per_machine'] == 1:
        options['num_machines'] = int(1.5*options['num_machines'])
        options['num_mpiprocs_per_machine'] *= 2
        options['num_cores_per_mpiproc'] /= 2

    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_options = find_parallelism_qp(options['num_machines'], options['num_mpiprocs_per_machine']/2, \
                                                        options['num_cores_per_mpiproc']*2, bands, \
                                                        occupied, qp, kpoints,\
                                                        what, last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_options

def fix_time(options, restart, max_walltime):
    options['max_wallclock_seconds'] = \
                            int(options['max_wallclock_seconds']*1.3*restart)

    if options['max_wallclock_seconds'] > max_walltime:
        options['max_wallclock_seconds'] = max_walltime

    return options
