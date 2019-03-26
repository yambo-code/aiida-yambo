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

account = 'Pra15_3963'

ParameterData = DataFactory('parameter')

inputs = {}
inputs['settings'] = Dict(dict={'initialise': True})
inputs['_options'] = {
    'max_wallclock_seconds': 30 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    },
    'custom_scheduler_commands': u"#PBS -A" + account,
}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='p2y calculation.')
    parser.add_argument(
        '--code',
        type=str,
        dest='codename',
        required=True,
        help='The yambo code to use')
    parser.add_argument(
        '--precode',
        type=str,
        dest='precodename',
        required=True,
        help='The yambo precodename to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent',
        required=True,
        help='The parent to use')
    args = parser.parse_args()
    precode = Code.get_from_string(args.precodename)
    code = Code.get_from_string(args.codename)
    inputs['preprocessing_code'] = precode
    inputs['code'] = code
    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
    process = YamboCalculation.process()
    running = submit(process, **inputs)
    print("Created calculation; with pid={}".format(running.pid))
