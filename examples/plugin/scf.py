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
from aiida.engine import run_get_node
from aiida_yambo.calculations.gw import YamboCalculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida.orm import UpfData
from aiida.orm.nodes.data.upf import get_pseudos_from_structure


StructureData = DataFactory('structure')

a = 5.367 * pymatgen.core.units.bohr_to_ang
structure_pmg = pymatgen.Structure(
    lattice=[[-a, 0, a], [0, a, a], [-a, a, 0]],
    species=['Ga', 'As'],
    coords=[[0] * 3, [0.25] * 3])
structure = StructureData()
structure.set_pymatgen_structure(structure_pmg)

ParameterData = DataFactory('dict')

parameters = ParameterData(
    dict={
        'CONTROL': {
            'calculation': 'scf',
            'restart_mode': 'from_scratch',
            'wf_collect': True,
            'verbosity': 'high',
        },
        'SYSTEM': {
            'ecutwfc': 50.,
        },
        'ELECTRONS': {
            'conv_thr': 1.e-8,
            'electron_maxstep ': 50,
            'mixing_mode': 'plain',
            'mixing_beta': 0.7,
        }
    })

KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData()
kpoints.set_kpoints_mesh([8, 8, 8])

inputs = {}
inputs['structure'] = structure
inputs['settings'] = Dict(dict={})
inputs['kpoints'] = kpoints
inputs['parameters'] = parameters
options =  {
    'max_wallclock_seconds': 30 * 60,
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine":12,
    },
    'queue_name':'s3par6c',
#   'custom_scheduler_commands':
#   u"#SBATCH --account=Pra15_3963 \n" + "#SBATCH --partition=knl_usr_dbg \n" +
#   "#SBATCH --mem=86000 \n" + "\n" +
#   "\nexport OMP_NUM_THREADS=1\nexport MKL_NUM_THREADS=1"
}
inputs['metadata']={
    'options' : options,
    'label':'scf example',
}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='SCF calculation.')
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
    args = parser.parse_args()
    code = Code.get_from_string(args.codename)
    inputs['code'] = code
    inputs['pseudos'] = get_pseudos_from_structure(structure, args.pseudo)
    running = submit(PwCalculation, **inputs)
    print("Created calculation; with pk={}".format(running.pk))
