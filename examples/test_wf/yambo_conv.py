#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict
from aiida.engine import submit
from aiida_yambo.workflows.yamboconv import YamboConvergence
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from ase import Atoms


options = {
    'max_wallclock_seconds': 24*60*60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine":9,
        "num_cores_per_mpiproc":1,
    },
    'queue_name':'s3par',
    'environment_variables': {},
    'custom_scheduler_commands': u"#PBS -N example_gw \nexport OMP_NUM_THREADS=1",
    }

metadata = {
    'options':options,
    'label': 'example_gw',
}

params_scf = {
    'CONTROL': {
        'calculation': 'scf',
        'verbosity': 'high',
        'wf_collect': True
    },
    'SYSTEM': {
        'ecutwfc': 130.,
        'force_symmorphic': True,
        'nbnd': 150
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
        'ppa': True,
        'gw0': True,
        'HF_and_locXC': True,
        'em1d': True,
        'Chimod': 'hartree',
        #'EXXRLvcs': 40,
        #'EXXRLvcs_units': 'Ry',
        'BndsRnXp': [1, 60],
        'NGsBlkXp': 2,
        'NGsBlkXp_units': 'Ry',
        'GbndRnge': [1, 60],
        'DysSolver': "n",
        'QPkrange': [[1, 1, 8, 9]],
        'X_all_q_CPU': "1 1 3 3",
        'X_all_q_ROLEs': "q k c v",
        'SE_CPU': "1 1 9",
        'SE_ROLEs': "q qp b",
    }
params_gw = Dict(dict=params_gw)


builder = YamboConvergence.get_builder()


##################scf+nscf part of the builder
builder.ywfl.scf.pw.structure = structure
builder.ywfl.scf.pw.parameters = parameter_scf
builder.kpoints = kpoints
builder.ywfl.scf.pw.metadata.options.max_wallclock_seconds = options['max_wallclock_seconds']
builder.ywfl.scf.pw.metadata.options.resources = options['resources']
builder.ywfl.scf.pw.metadata.options.queue_name = options['queue_name']
builder.ywfl.scf.pw.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']

builder.ywfl.nscf.pw.structure = builder.ywfl.scf.pw.structure
builder.ywfl.nscf.pw.parameters = parameter_nscf
builder.ywfl.nscf.pw.metadata = builder.ywfl.scf.pw.metadata

##################yambo part of the builder
builder.ywfl.yres.gw.metadata.options.max_wallclock_seconds = options['max_wallclock_seconds']
builder.ywfl.yres.gw.metadata.options.resources = options['resources']
builder.ywfl.yres.gw.metadata.options.queue_name = options['queue_name']
builder.ywfl.yres.gw.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']
builder.ywfl.yres.gw.parameters = params_gw
builder.ywfl.yres.gw.precode_parameters = Dict(dict={})
builder.ywfl.yres.gw.settings = Dict(dict={'INITIALISE': False, 'RESTART': False})
builder.ywfl.yres.max_restarts = Int(5)

var_to_conv = [{'var':'bands','delta': 50, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.03, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'NGsBlkXp','delta': 1, 'steps': 3, 'max_restarts': 5, \
                            'conv_thr': 0.03, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'bands','delta': 50, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.025, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'NGsBlkXp','delta': 1, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.025, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'bands','delta': 50, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.02, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'NGsBlkXp','delta': 1, 'steps': 3, 'max_restarts': 5, \
                            'conv_thr': 0.02, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'kpoints','delta': 1, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.02, 'conv_window': 3, 'starting_k_distance': 5},
               {'var':'bands','delta': 50, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.02, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'NGsBlkXp','delta': 1, 'steps': 3, 'max_restarts': 5, \
                            'conv_thr': 0.02, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},
               {'var':'kpoints','delta': 1, 'steps': 3, 'max_restarts': 5, \
                             'conv_thr': 0.02, 'conv_window': 3, 'what':'gap','where':[(1,1)], \
                             'where_word':['Gamma'],},]


for i in range(len(var_to_conv)):
    print('{}-th variable will be {}'.format(i+1,var_to_conv[i]['var']))
var_to_conv.reverse()
builder.var_to_conv = List(list = var_to_conv)




if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    parser.add_argument(
        '--yambocode',
        type=int,
        dest='yambocode_pk',
        required=True,
        help='The yambo(main code) codename to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=True,
        help='The parent to use')
    parser.add_argument(
        '--yamboprecode',
        type=int,
        dest='yamboprecode_pk',
        required=False,
        help='The precode to use')
    parser.add_argument(
        '--pwcode',
        type=int,
        dest='pwcode_pk',
        required=False,
        help='The pw to use')
    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo_family',
        required=False,
        help='The pseudo_family')


    args = parser.parse_args()
    builder.ywfl.yres.gw.preprocessing_code = load_node(args.yamboprecode_pk)
    builder.ywfl.yres.gw.code = load_node(args.yambocode_pk)
    builder.parent_folder = load_node(args.parent_pk).outputs.remote_folder

    builder.ywfl.scf.pw.code = load_node(args.pwcode_pk)
    builder.ywfl.nscf.pw.code = load_node(args.pwcode_pk)
    builder.ywfl.scf.pw.pseudos = validate_and_prepare_pseudos_inputs(
                builder.ywfl.pw.structure, pseudo_family = Str(args.pseudo_family))
    builder.ywfl.nscf.pw.pseudos = builder.ywfl.scf.pw.pseudos

    running = submit(builder)
    print("Created calculation; with pk={}".format(running.pk))
