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
def fix_parallelism(resources, failed_calc):

    what = ['bands']
    bands, qp, last_qp, runlevels = find_gw_info(failed_calc)
    occupied, kpoints = take_filled_states(failed_calc.pk), take_number_kpts(failed_calc.pk)


    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine'], \
                                                        resources['num_cores_per_mpiproc'], bands, \
                                                        occupied, qp, kpoints,\
                                                        what, last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_resources

def fix_memory(resources, failed_calc, exit_status):

    if exit_status == 505:
        what = ['bands']
    else:
        what = ['bands','g'] 
        
    bands, qp, last_qp, runlevels = find_gw_info(failed_calc)
    occupied, kpoints = take_filled_states(failed_calc.pk), take_number_kpts(failed_calc.pk)

    if failed_calc.outputs.output_parameters.get_dict()['has_gpu']: #or mpi = 1...but there should be a limit
        resources['num_machines'] = int(1.5*resources['num_machines'])
        resources['num_machines'] += resources['num_machines']%2
        resources['num_mpiprocs_per_machine'] *= 2
        resources['num_cores_per_mpiproc'] /= 2

    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine']/2, \
                                                        resources['num_cores_per_mpiproc']*2, bands, \
                                                        occupied, qp, kpoints,\
                                                        what, last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_resources

def fix_time(options, restart, max_walltime):
    options['max_wallclock_seconds'] = \
                            int(options['max_wallclock_seconds']*1.3*restart)

    if options['max_wallclock_seconds'] > max_walltime:
        options['max_wallclock_seconds'] = max_walltime

    return options
