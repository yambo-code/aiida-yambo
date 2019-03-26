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
        'CONTROL': {
            'calculation': 'nscf',
            'restart_mode': 'from_scratch',
            'wf_collect': True,
            'verbosity': 'high',
        },
        'SYSTEM': {
            'ecutwfc': 80.,
            'nbnd': 50,
            'force_symmorphic': True,
        },
        'ELECTRONS': {
            'conv_thr': 1.e-10,
            'diago_full_acc': True,
            'diagonalization': 'cg',
        }
    })

KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData()
kpoints.set_kpoints_mesh([6, 6, 6])

inputs = {}
inputs['kpoints'] = kpoints
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
    "\nexport OMP_NUM_THREADS=1\nexport MKL_NUM_THREADS=1"
}

num_pools = 8
inputs['settings'] = Dict(dict={'cmdline': ['-nk', str(num_pools)]})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='NSCF calculation.')
    parser.add_argument(
        '--code',
        type=str,
        dest='codename',
        required=True,
        help='The pw codename to use')
    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo',
        required=True,
        help='The pseudo family to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent',
        required=True,
        help='The parent  to use')
    args = parser.parse_args()
    code = Code.get_from_string(args.codename)
    structure = load_node(args.parent).inp.structure
    inputs['structure'] = structure
    inputs['pseudo'] = get_pseudos_from_structure(structure, args.pseudo)
    inputs['code'] = code
    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
    process = PwCalculation.process()
    running = submit(process, **inputs)
    print("Created calculation; with pid={}".format(running.pid))
