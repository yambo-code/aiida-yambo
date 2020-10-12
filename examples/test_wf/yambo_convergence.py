#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict
from aiida.engine import submit
from aiida_yambo.workflows.yamboconvergence import YamboConvergence
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
    kpoints.set_kpoints_mesh([6,6,2])

    ###### setting the scf parameters ######

    Dict = DataFactory('dict')
    params_scf = {
        'CONTROL': {
            'calculation': 'scf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': 130.,
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
            'ecutwfc': 130.,
            'force_symmorphic': True,
            'nbnd': 500
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

    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([6,6,2])

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


    params_gw = {
            'HF_and_locXC': True,
            'dipoles': True,
            'ppa': True,
            'gw0': True,
            'em1d': True,
            'Chimod': 'hartree',
            #'EXXRLvcs': 40,
            #'EXXRLvcs_units': 'Ry',
            'BndsRnXp': [1, 10],
            'NGsBlkXp': 2,
            'NGsBlkXp_units': 'Ry',
            'GbndRnge': [1, 10],
            'DysSolver': "n",
            'QPkrange': [[1, 1, 8, 9]],
            'DIP_CPU': "1 1 1",
            'DIP_ROLEs': "k c v",
            'X_CPU': "1 1 1 1",
            'X_ROLEs': "q k c v",
            'SE_CPU': "1 1 1",
            'SE_ROLEs': "q qp b",
        }
    params_gw = Dict(dict=params_gw)


    builder = YamboConvergence.get_builder()


    ##################scf+nscf part of the builder
    builder.ywfl.scf.pw.structure = structure
    builder.ywfl.scf.pw.parameters = parameter_scf
    builder.kpoints = kpoints
    builder.ywfl.scf.pw.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.ywfl.scf.pw.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.ywfl.scf.pw.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.ywfl.scf.pw.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.ywfl.scf.pw.metadata.options.account = options['account']

    builder.ywfl.scf.pw.metadata.options.prepend_text = options['prepend_text']

    builder.ywfl.nscf.pw.structure = builder.ywfl.scf.pw.structure
    builder.ywfl.nscf.pw.parameters = parameter_nscf
    builder.ywfl.nscf.pw.metadata = builder.ywfl.scf.pw.metadata

    builder.ywfl.scf.pw.code = load_code(options['pwcode_id'])
    builder.ywfl.nscf.pw.code = load_code(options['pwcode_id'])
    builder.ywfl.scf.pw.pseudos = validate_and_prepare_pseudos_inputs(
                builder.ywfl.scf.pw.structure, pseudo_family = Str(options['pseudo_family']))
    builder.ywfl.nscf.pw.pseudos = builder.ywfl.scf.pw.pseudos

    ##################yambo part of the builder
    builder.ywfl.yres.yambo.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.ywfl.yres.yambo.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.ywfl.yres.yambo.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.ywfl.yres.yambo.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.ywfl.yres.yambo.metadata.options.account = options['account']

    builder.ywfl.yres.yambo.parameters = params_gw
    builder.ywfl.yres.yambo.precode_parameters = Dict(dict={})
    builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': False})
    builder.ywfl.yres.max_iterations = Int(5)

    builder.ywfl.yres.yambo.preprocessing_code = load_code(options['yamboprecode_id'])
    builder.ywfl.yres.yambo.code = load_code(options['yambocode_id'])
    try:
        builder.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
    except:
        pass

    builder.p2y = builder.ywfl
    builder.precalc = builder.ywfl #for simplicity, to specify if PRE_CALC is True

    builder.workflow_settings = Dict(dict={'type':'1D_convergence',
                                           'what':'gap',
                                           'where':[(1,8,1,9)],
                                           'PRE_CALC': False,})

    #'what': 'single-levels','where':[(1,8),(1,9)]
    var_to_conv = [{'var':['BndsRnXp','GbndRnge'],'delta': [[0,10],[0,10]], 'steps': 2, 'max_iterations': 3, \
                                 'conv_thr': 0.2, 'conv_window': 2},
                   {'var':'NGsBlkXp','delta': 1, 'steps': 2, 'max_iterations': 3, \
                                'conv_thr': 0.2, 'conv_window': 2},
                  # {'var':['BndsRnXp','GbndRnge'],'delta': [[0,10],[0,10]], 'steps': 2, 'max_iterations': 5, \
                  #               'conv_thr': 0.1, 'conv_window': 2},
                   #{'var':'NGsBlkXp','delta': 1, 'steps': 2, 'max_iterations': 3, \
                    #             'conv_thr': 0.1, 'conv_window': 2},]
                   {'var':'kpoints','delta': 1, 'steps': 2, 'max_iterations': 2, \
                                 'conv_thr': 0.1, 'conv_window': 2}]


    for i in range(len(var_to_conv)):
        print('{}-th variable will be {}'.format(i+1,var_to_conv[i]['var']))

    builder.parameters_space = List(list = var_to_conv)

    return builder
    
if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    print("Submitted YamboConvergence; with pk=< {} >".format(running.pk))
