from __future__ import absolute_import
from __future__ import print_function
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.yambowf import YamboWorkflow

try:
    from aiida.orm.nodes.base import Float, Str, NumericType, BaseType, Bool, List
    from aiida.engine.run import run, submit
except ImportError:
    from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData, Bool
    from aiida.workflows2.db_types import SimpleData as BaseType
    from aiida.orm.nodes.simple import SimpleData as SimpleData_
    from aiida.workflows2.run import run

from aiida.plugins.utils import DataFactory
ParameterData = DataFactory("parameter")
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

struc.store()

pw_parameters = {
    'CONTROL': {
        'calculation': 'scf',
        'restart_mode': 'from_scratch',
        'wf_collect': True,
        'tprnfor': True,
        'etot_conv_thr': 0.00001,
        'forc_conv_thr': 0.0001,
        'verbosity': 'high',
    },
    'SYSTEM': {
        'ecutwfc': 35.,
    },
    'ELECTRONS': {
        'conv_thr': 1.e-8,
        'electron_maxstep ': 100,
        'mixing_mode': 'plain',
        'mixing_beta': 0.3,
    }
}

pw_nscf_parameters = {
    'CONTROL': {
        'calculation': 'nscf',
        'restart_mode': 'from_scratch',
        'wf_collect': True,
        'tprnfor': True,
        'etot_conv_thr': 0.00001,
        'forc_conv_thr': 0.0001,
        'verbosity': 'high',
    },
    'SYSTEM': {
        'ecutwfc': 20.,
        'nbnd': 40,
        'force_symmorphic': True,
    },
    'ELECTRONS': {
        'conv_thr': 1.e-8,
        'electron_maxstep ': 100,
        'mixing_mode': 'plain',
        'mixing_beta': 0.3,
    }
}

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

calculation_set_pw = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2
    },
    'max_wallclock_seconds': 60 * 30, #'max_memory_kb': 1 * 88 * 1000000,
    "queue_name":"s3par8c",
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
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
        ],
        'INITIALISE':
        False
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
        required=True,
        help='The pw codename to use')
    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo',
        required=True,
        help='The pesudo  to use')
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
        required=False,
        help='QE scf/nscf / yambo calculation ')

    parser.add_argument(
        '--parent-workchain',
        type=int,
        dest='parent_workchain',
        required=False,
        help=' Parent yambo workflow ')
    args = parser.parse_args()
    if not args.structure:
        structure = struc
    else:
        structure = load_node(int(args.structure))  #1791
    parent_calc = None
    if args.parent:
        parent_calc = load_node(int(args.parent))  #1791
    kwargs = {
        "codename_pw": Str(args.pwcode),
        "codename_p2y": Str(args.precode),
        "codename_yambo": Str(args.yambocode),
        "pseudo_family": Str(args.pseudo),
        "calculation_set_pw": Dict(dict=calculation_set_pw),
        "calculation_set_p2y": Dict(dict=calculation_set_p2y),
        "calculation_set_yambo": Dict(dict=calculation_set_yambo),
        "settings_pw": settings_pw,
        "settings_p2y": settings_p2y,
        "settings_yambo": settings_yambo,
        "input_pw": Dict(dict={}),
        "structure": structure,
        "kpoint_pw": kpoints,
        "gamma_pw": Bool(False),
        "parameters_pw": Dict(dict=pw_parameters),
        "parameters_pw_nscf": Dict(dict=pw_nscf_parameters),
        "parameters_p2y": Dict(dict=yambo_parameters),
        "parameters_yambo": Dict(dict=yambo_parameters),
    }
    if parent_calc:
        kwargs["parent_folder"] = parent_calc.out.remote_folder
    if args.parent_workchain:
        kwargs["previous_yambo_workchain"] = Str(args.parent_workchain)
    full_result = run(YamboWorkflow, **kwargs)
    print(("Workflow submited :", full_result))
