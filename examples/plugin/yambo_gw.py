#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List
from aiida.orm import Code
from aiida.plugins import DataFactory
import pymatgen
from aiida.engine import submit
from aiida_yambo.calculations.gw import YamboCalculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida.orm import UpfData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure

Dict = DataFactory('dict')

parameters = dict={
        'ppa': True,
        'gw0': True,
        'HF_and_locXC': True,
        'em1d': True,
        'Chimod': 'hartree',
        'EXXRLvcs': 10,
        'EXXRLvcs_units': 'Ry',
        'BndsRnXp': (1, 30),
        'NGsBlkXp': 1,
        'NGsBlkXp_units': 'Ry',
        'GbndRnge': (1, 30),
        'DysSolver': "n",
        'QPkrange': [(1, 1, 1, 15)],
        'X_all_q_CPU': "1 1 6 2",
        'X_all_q_ROLEs': "q k c v",
        #'SE_CPU': "1 1 12",
        #'SE_ROLEs': "q qp b",
    }

inputs = {}
inputs['settings'] = Dict(dict={'INITIALISE': False})
options =  {
    'max_wallclock_seconds': 30 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine":12,
        },
    'custom_scheduler_commands': u"#PBS -q s3par6c",
    }

inputs['metadata']={
    'options' : options,
    'label':'prova',
}
inputs['parameters']=Dict(dict=parameters)
inputs['precode_parameters']=Dict(dict={})

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
    parser.add_argument(
        '--precode',
        type=str,
        dest='precodename',
        required=False,
        help='The precode to use')

    args = parser.parse_args()
    precode = Code.get_from_string(args.precodename)
    code = Code.get_from_string(args.codename)
    inputs['preprocessing_code'] = precode
    inputs['main_code'] = code
    inputs['code'] = code
    inputs['parent_folder'] = load_node(args.parent).outputs.remote_folder
    running = submit(YamboCalculation, **inputs)
    print("Created calculation; with pk={}".format(running.pk))
