#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict
from aiida.engine import submit
from aiida_yambo.calculations.gw import YamboCalculation


options = {
    'max_wallclock_seconds': 24*60*60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine":1,
        "num_cores_per_mpiproc":1,
    },
#    'queue_name':'s3par',
    'environment_variables': {},
#    'custom_scheduler_commands': u"#PBS -N example_gw \nexport OMP_NUM_THREADS=1",
    }

metadata = {
    'options':options,
    'label': 'example_gw',
}

builder = YamboCalculation.get_builder()
builder.metadata.options.max_wallclock_seconds = \
        options['max_wallclock_seconds']
builder.metadata.options.resources = \
        dict = options['resources']
#builder.metadata.options.queue_name = options['queue_name']
#builder.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']
builder.precode_parameters = Dict(dict={})
builder.settings = Dict(dict={'INITIALISE': False})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    parser.add_argument(
        '--code',
        type=int,
        dest='code_pk',
        required=True,
        help='The yambo(main code) codename to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=True,
        help='The parent to use')
    parser.add_argument(
        '--precode',
        type=int,
        dest='precode_pk',
        required=False,
        help='The precode to use')

    args = parser.parse_args()
    builder.preprocessing_code = load_node(args.precode_pk)
    builder.code = load_node(args.code_pk)
    builder.parent_folder = load_node(args.parent_pk).outputs.remote_folder
    running = submit(builder)
    print("Created p2y calculation; with pk={}".format(running.pk))
