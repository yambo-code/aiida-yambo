#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict, Str,UpfData
from aiida.engine import submit
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from ase import Atoms
import argparse
from aiida_yambo.calculations.ypp import YppCalculation

def get_options():

    parser = argparse.ArgumentParser(description='YPP calculation.')
    parser.add_argument(
        '--yppcode',
        type=str,
        dest='yppcode_id',
        required=True,
        help='The ypp(main code) codename to use')

    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=True,
        help='The YamboCalculation parent to use')

    parser.add_argument(
        '--time',
        type=int,
        dest='max_wallclock_seconds',
        required=False,
        default=24*60*60,
        help='max wallclock in seconds')

    parser.add_argument(
        '--nodes',
        type=int,
        dest='num_machines',
        required=False,
        default=1,
        help='number of machines')

    parser.add_argument(
        '--mpi',
        type=int,
        dest='num_mpiprocs_per_machine',
        required=False,
        default=1,
        help='number of mpi processes per machine')

    parser.add_argument(
        '--threads',
        type=int,
        dest='num_cores_per_mpiproc',
        required=False,
        default=1,
        help='number of threads per mpi process')

    parser.add_argument(
        '--queue_name',
        type=str,
        dest='queue_name',
        required=False,
        default=None,
        help='queue(PBS) or partition(SLURM) name')

    parser.add_argument(
        '--qos',
        type=str,
        dest='qos',
        required=False,
        default=None,
        help='qos name')

    parser.add_argument(
        '--account',
        type=str,
        dest='account',
        required=False,
        default=None,
        help='account name')

    args = parser.parse_args()

    ###### setting the machine options ######
    options = {
        'yppcode_id': args.yppcode_id,
        'max_wallclock_seconds': args.max_wallclock_seconds,
        'resources': {
            "num_machines": args.num_machines,
            "num_mpiprocs_per_machine": args.num_mpiprocs_per_machine,
            "num_cores_per_mpiproc": args.num_cores_per_mpiproc,
        },
        'prepend_text': u"export OMP_NUM_THREADS="+str(args.num_cores_per_mpiproc),
        }

    if args.parent_pk:
        options['parent_pk']=args.parent_pk

    if args.queue_name:
        options['queue_name']=args.queue_name

    if args.qos:
        options['qos']=args.qos

    if args.account:
        options['account']=args.account

    return options

def main(options):

    params_gw = {'arguments':['electrons', 'bnds',],
                 'variables':{'OutputAlat': [4.716, ''],
                'INTERP_Shell_Fac': [20.0, ''],
                'BANDS_steps': [30.0, ''],
                'INTERP_mode': 'NN',
                'cooIn': 'rlu',
                'cooOut': 'rlu',
                'CIRCUIT_E_DB_path': 'none',
                'BANDS_bands': [[6, 11], ''],
                'INTERP_Grid': [['-1', '-1', '-1'], ''],
                'BANDS_kpts':[[[0.33300,-.66667,0.00000,],
                                [0.00000,0.00000,0.00000,],
                                [0.50000,-.50000,0.00000,],
                                [0.33300,-.66667,0.00000,],
                                [0.33300,-.66667,0.50000 ],
                                [0.00000,0.00000,0.50000,],
                                [0.50000,-.50000,0.50000,]],'']}}


    params_gw = Dict(dict=params_gw)


    builder = YppCalculation.get_builder()

    ##################yambo part of the builder
    builder.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.metadata.options.account = options['account']

    builder.parameters = params_gw

    builder.code = load_code(options['yppcode_id'])


    builder.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
    

    return builder

if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    print("Submitted YppCalculation; with pk=< {} >".format(running.pk))
