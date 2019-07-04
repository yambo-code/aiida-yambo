#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from aiida import load_profile
load_profile()

from aiida_yambo.workflows.yamborestart import YamboRestartWf


from aiida.orm import Float, Str, Dict, NumericType, BaseType
from aiida.orm import RemoteData
from aiida.orm import Code
from aiida.orm import StructureData

from aiida.engine import run, submit


from aiida.plugins import DataFactory


StructureData = DataFactory('structure')

cell = [
    [4.2262023163, 0.0000000000, 0.0000000000],
    [0.0000000000, 4.2262023163, 0.0000000000],
    [0.0000000000, 0.0000000000, 2.7009939524],
]
struc = StructureData(cell=cell)
struc.append_atom(
    position=(1.2610450495, 1.2610450495, 0.0000000000), symbols='O')
struc.append_atom(
    position=(0.8520622471, 3.3741400691, 1.3504969762), symbols='O')
struc.append_atom(
    position=(2.9651572668, 2.9651572668, 0.0000000000), symbols='O')
struc.append_atom(
    position=(3.3741400691, 0.8520622471, 1.3504969762), symbols='O')
struc.append_atom(
    position=(0.0000000000, 0.0000000000, 0.0000000000), symbols='Ti')
struc.append_atom(
    position=(2.1131011581, 2.1131011581, 1.3504969762), symbols='Ti')

#struc.store()

yambo_parameters ={
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
        'QPkrange': [(1, 1, 1, 16)],
        'X_all_q_CPU': "1 1 6 2",
        'X_all_q_ROLEs': "q k c v",
        'SE_CPU': "1 1 12",
        'SE_ROLEs': "q qp b",
    }

calculation_set_p2y = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 12
    },
    'max_wallclock_seconds': 60 * 30, #'max_memory_kb': 1 * 88 * 1000000,
    "queue_name":"s3par8c",
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
}

calculation_set_yambo = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 16
    },
    'max_wallclock_seconds':30, #'max_memory_kb': 1 * 10 * 1000000,
    "queue_name": "s3par8c",  # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
}



settings_pw = Dict(dict={})

settings_p2y = Dict(
    dict={
        "ADDITIONAL_RETRIEVE_LIST": [
            'r-*', 'o-*', 'l-*', 'l_*', 'LOG/l-*_CPU_1', 'aiida/ndb.QP',
            'aiida/ndb.HF_and_locXC'
        ],
        'INITIALISE':
        True
    })

settings_yambo = Dict(
    dict={
        "ADDITIONAL_RETRIEVE_LIST": [
            'r-*', 'o-*', 'l-*', 'l_*', 'LOG/l-*_CPU_1', 'aiida/ndb.QP',
            'aiida/ndb.HF_and_locXC'
        ]
    })

KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData()
kpoints.set_kpoints_mesh([2, 2, 2])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='GW QP calculation.')
    parser.add_argument(
        '--precode',
        type=str,
        dest='precode',
        required=True,
        help='The p2y codename to use')
    parser.add_argument(
        '--yambocode',
        type=str,
        dest='yambocode',
        required=True,
        help='The yambo codename to use')

    parser.add_argument(
        '--pwcode',
        type=str,
        dest='pwcode',
        required=False,
        help='The pw codename to use')
    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo',
        required=False,
        help='The pseudo  to use')
    parser.add_argument(
        '--structure',
        type=int,
        dest='structure',
        required=False,
        help='The structure  to use')
    parser.add_argument(
        '--parent',
        type=int,
        dest='parent',
        required=True,
        help='The parent to use')

    args = parser.parse_args()
    if not args.structure:
        structure = struc
    else:
        structure = load_node(int(args.structure))  #1791
    parentcalc = load_node(int(args.parent))
    parent_folder_ = parentcalc.outputs.remote_folder
    p2y_result = submit(
        YamboRestartWf,
        precode=Str(args.precode),
        yambocode=Str(args.yambocode),
        parameters=Dict(dict=yambo_parameters),
        calculation_set=Dict(dict=calculation_set_yambo),
        parent_folder=parent_folder_,
        settings=settings_yambo)

    print(("Workflow launched: ", p2y_result))
