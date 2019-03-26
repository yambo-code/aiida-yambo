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
        'optics': True,
        'chi': True,
        'Chimod': "IP",
        'QpntsRXd': (1., 1.),
        'BndsrnXd': (1., 20.),
        'FFTGvecs': 50,
        'FFTGvecs_units': 'Ry',
        # 'NGsBlkXd': 1,              #For Hartree
        # 'NGsBlkXd_units': 'RL',
        'EnRngeXd': (0.00, 10.),
        'EnRngeXd_units': 'eV',
        'DmRngeXd': (0.15, 0.3),
        'DmRngeXd_units': 'eV',
        'ETStpsXd': 1000,
        'LongDrXd': (1., 0.0, 0.0),
        'X_all_q_CPU': "1 1 8 4",
        'X_all_q_ROLEs': "q k c v",
    })

inputs = {}
inputs['parameters'] = parameters
inputs['_options'] = {
    'max_wallclock_seconds':
    30 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 64,
    },
    'custom_scheduler_commands':
    u"#SBATCH --account=Pra15_3963 \n" + "#SBATCH --partition=knl_usr_dbg \n" +
    "#SBATCH --mem=86000 \n" + "\n" +
    "\nexport OMP_NUM_THREADS=2\nexport MKL_NUM_THREADS=2"
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
