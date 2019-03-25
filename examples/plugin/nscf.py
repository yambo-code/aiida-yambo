#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.orm import DataFactory, CalculationFactory
from aiida.common.example_helpers import test_and_get_code
from aiida.orm.data.base import List
from aiida.orm import Code
from aiida.orm import DataFactory
import pymatgen
from aiida.work.run import submit
from aiida_yambo.calculations.gw import YamboCalculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida.orm.data.upf import UpfData, get_pseudos_from_structure

ParameterData = DataFactory('parameter')

parameters = ParameterData(
    dict={
        'CONTROL': {
            'calculation': 'nscf',
            'restart_mode': 'from_scratch',
            'wf_collect': True,
            'verbosity': 'high',
        },
        'SYSTEM': {
            'ecutwfc': 50.,
            'nbnd': 50,
            'force_symmorphic': True,
        },
        'ELECTRONS': {
            'conv_thr': 1.e-8,
            'electron_maxstep ': 50,
            'diago_full_acc': True,
            'mixing_beta': 0.7,
        }
    })

KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData()
kpoints.set_kpoints_mesh([6, 6, 6])

inputs = {}
inputs['kpoints'] = kpoints
inputs['parameters'] = parameters
inputs['_options'] = {
    'max_wallclock_seconds': 10 * 60,
    'resources': {
        "num_machines": 1,
        #"num_mpiprocs_per_machine":16,
    },
    #'custom_scheduler_commands':u"#PBS -A Pra15_3963",
}

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
