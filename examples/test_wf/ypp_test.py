#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict, Str,UpfData
from aiida.engine import submit
from aiida_yambo.workflows.yambowf import YamboWorkflow
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from ase import Atoms
import argparse

def get_options():

    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    parser.add_argument(
        '--yambocode',
        type=str,
        dest='yambocode_id',
        required=True,
        help='The yambo(main code) codename to use')

    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=False,
        help='The parent to use')

    parser.add_argument(
        '--yamboprecode',
        type=str,
        dest='yamboprecode_id',
        required=True,
        help='The precode to use')

    parser.add_argument(
        '--pwcode',
        type=str,
        dest='pwcode_id',
        required=True,
        help='The pw to use')

    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo_family',
        required=True,
        help='The pseudo_family')

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
        'yambocode_id': args.yambocode_id,
        'yamboprecode_id': args.yamboprecode_id,
        'pwcode_id': args.pwcode_id,
        'pseudo_family': args.pseudo_family,
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

    ###### setting the lattice structure ######

    alat = 2.4955987320 # Angstrom
    the_cell = [[1.000000*alat,   0.000000,   0.000000],
                [-0.500000*alat,  0.866025*alat,   0.000000],
                [0.000000,   0.000000,  6.4436359260]]

    atoms = Atoms('BNNB', [(1.2477994910, 0.7204172280, 0.0000000000),
    (-0.0000001250, 1.4408346720, 0.0000000000),
    (1.2477994910, 0.7204172280, 3.2218179630),
    (-0.0000001250,1.4408346720, 3.2218179630)],
    cell = [1,1,1])
    atoms.set_cell(the_cell, scale_atoms=False)
    atoms.set_pbc([True,True,True])

    StructureData = DataFactory('structure')
    structure = StructureData(ase=atoms)

    ###### setting the kpoints mesh ######

    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([8,8,1])

    ###### setting the scf parameters ######

    Dict = DataFactory('dict')
    params_scf = {
        'CONTROL': {
            'calculation': 'scf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': 60.,
            'force_symmorphic': True,
            'nbnd': 20
        },
        'ELECTRONS': {
            'mixing_mode': 'plain',
            'mixing_beta': 0.7,
            'conv_thr': 1.e-8,
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }

    parameter_scf = Dict(dict=params_scf)

    params_nscf = {
        'CONTROL': {
            'calculation': 'nscf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': 60.,
            'force_symmorphic': True,
            'nbnd': 50
        },
        'ELECTRONS': {
            'mixing_mode': 'plain',
            'mixing_beta': 0.6,
            'conv_thr': 1.e-8,
            'diagonalization': 'david',
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }

    parameter_nscf = Dict(dict=params_nscf)

    params_gw = {'arguments':['rim_cut', 'dipoles', 'gw0', 'HF_and_locXC', 'ppa'],
                 'variables':{
                'GTermEn': [250.0, 'mHa'],
                'NGsBlkXp': [1.0, 'Ry'],
                'PPAPntXp': [30.0, 'eV'],
                'CUTRadius': [13.228083, ''],
                'CUTGeo': 'sphere xyz',
                'Chimod': 'hartree',
                'DysSolver': 'n',
                'GTermKind': 'BG',
                'BndsRnXp': [[1, 50], ''],
                'GbndRnge': [[1, 50], ''],
                'QPkrange': [[[1, 10, 6, 11],], ''],
                }}


    params_gw = Dict(dict=params_gw)


    builder = YamboWorkflow.get_builder()


    ##################scf+nscf part of the builder
    builder.structure = structure
    #builder.scf_parameters = parameter_scf
    builder.scf.kpoints = kpoints
    builder.nscf.kpoints = kpoints
    builder.scf.pw.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.scf.pw.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.scf.pw.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.scf.pw.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.scf.pw.metadata.options.account = options['account']

    builder.scf.pw.metadata.options.prepend_text = options['prepend_text']

    #builder.structure = builder.structure
    #builder.nscf_parameters = parameter_nscf
    #builder.nscf.kpoints = builder.scf.kpoints
    builder.nscf.pw.metadata = builder.scf.pw.metadata

    builder.pw_code = load_code(options['pwcode_id'])
    #builder.nscf.pw.code = load_code(options['pwcode_id'])
    builder.scf.pw.pseudos = validate_and_prepare_pseudos_inputs(
                builder.structure, pseudo_family = Str(options['pseudo_family']))

    ##################yambo part of the builder
    builder.yres.yambo.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.yres.yambo.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.yres.yambo.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.yres.yambo.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.yres.yambo.metadata.options.account = options['account']

    builder.yres.yambo.parameters = params_gw
    builder.yres.yambo.precode_parameters = Dict(dict={})
    builder.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': False, 'T_VERBOSE':True,})
    builder.yres.max_iterations = Int(5)

    builder.additional_parsing = List(list=['gap_','G_v','gap_GG','gap_GY','gap_GK','gap_KK','gap_GM',('O',[0.125,0.125,0.0]),('gap_ok',[[0,0.5,0],[0.125,0.125,0.0]]) ])

    builder.yres.yambo.preprocessing_code = load_code(options['yamboprecode_id'])
    builder.yres.yambo.code = load_code(options['yambocode_id'])
    try:
        builder.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
        builder.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': True, 'T_VERBOSE':True,})
    except:
        pass

    return builder

if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    print("Submitted YamboWorkflow workchain; with pk=< {} >".format(running.pk))
