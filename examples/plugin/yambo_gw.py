#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.common.example_helpers import test_and_get_code
from aiida.orm.nodes.base import List
from aiida.orm import Code
from aiida.plugins import DataFactory
import pymatgen
from aiida.engine.run import submit
from aiida_yambo.calculations.gw import YamboCalculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida.orm.nodes.upf import UpfData, get_pseudos_from_structure

ParameterData = DataFactory('parameter')

parameters = Dict(
    dict={
        'ppa': True,
        'gw0': True,
        'HF_and_locXC': True,
        'em1d': True,
        'Chimod': 'hartree',
        'EXXRLvcs': 10,
        'EXXRLvcs_units': 'Ry',
        'BndsRnXp': (1, 50),
        'NGsBlkXp': 2,
        'NGsBlkXp_units': 'Ry',
        'GbndRnge': (1, 50),
        'DysSolver': "n",
        'QPkrange': [(1, 1, 9, 10)],
        'X_all_q_CPU': "1 1 8 2",
        'X_all_q_ROLEs': "q k c v",
        'SE_CPU': "1 2 8",
        'SE_ROLEs': "q qp b",
    })

inputs = {}
inputs['parameters'] = parameters
inputs['_options'] = {
    'max_wallclock_seconds': 30 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 16,
    },
    #'custom_scheduler_commands':u"#SBATCH  --partition=debug",
    #'custom_scheduler_commands':u"#PBS -A Pra15_3963
    #                              \nexport OMP_NUM_THREADS=64
    #                              \nexport MKL_NUM_THREADS=64",
}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    parser.add_argument(
        '--code',
        type=str,
        dest='codename',
        required=True,
        help='The pw codename to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent',
        required=True,
        help='The parent  to use')
    args = parser.parse_args()
    code = Code.get_from_string(args.codename)
    inputs['code'] = code
    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
    process = YamboCalculation.process()
    running = submit(process, **inputs)
    print("Created calculation; with pid={}".format(running.pid))
