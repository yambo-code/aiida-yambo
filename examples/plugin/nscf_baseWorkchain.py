#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory
from aiida.engine import submit
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from ase import Atoms

###### setting the machine options ######
options = {
    'max_wallclock_seconds': 24* 60 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine":1,
#        "num_cores_per_mpiproc":2,
    },
#    'queue_name':'s3par',
    'environment_variables': {},
#    'custom_scheduler_commands': u"#PBS -N hBN_gw \nexport OMP_NUM_THREADS=2",
    }

metadata = {
    'options':options,
    'label': 'hBN -scf- workchain',
}

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

###### setting the nscf parameters ######

Dict = DataFactory('dict')
params_scf = {
    'CONTROL': {
        'calculation': 'nscf',
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

###### creation of the workchain ######

builder = PwBaseWorkChain.get_builder()
builder.pw.structure = structure
builder.pw.parameters = parameter_scf
builder.kpoints = kpoints
builder.pw.metadata.options.max_wallclock_seconds = \
        options['max_wallclock_seconds']
builder.pw.metadata.options.resources = \
        dict = options['resources']
#builder.pw.metadata.options.queue_name = options['queue_name']
#builder.pw.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']

###### inputs parameters, to be provided from shell ######

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='SCF calculation.')
    parser.add_argument(
        '--code',
        type=int,
        dest='code_pk',
        required=True,
        help='The pw codename to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=True,
        help='The parent to use')

    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo_family',
        required=True,
        help='The pseudo family to use')
    args = parser.parse_args()
    builder.pw.code = load_node(args.code_pk)
    builder.pw.pseudos = validate_and_prepare_pseudos_inputs(
                builder.pw.structure, pseudo_family = Str(args.pseudo_family))
    builder.pw.parent_folder = load_node(args.parent_pk).outputs.remote_folder

    running = submit(builder)
    print("Submitted PwBaseWorkchain; with pk={}".format(running.pk))
