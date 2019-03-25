from __future__ import absolute_import
from __future__ import print_function
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.yambowf import YamboWorkflow

try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType, Bool, List
    from aiida.work.run import run, submit
except ImportError:
    from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData, Bool
    from aiida.workflows2.db_types import SimpleData as BaseType
    from aiida.orm.data.simple import SimpleData as SimpleData_
    from aiida.workflows2.run import run

from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')

from ase.spacegroup import crystal
a = 5.388
cell = crystal(
    'Si', [(0, 0, 0)],
    spacegroup=227,
    cellpar=[a, a, a, 90, 90, 90],
    primitive_cell=True)
struc = StructureData(ase=cell)

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
        'ecutwfc': 20.,
    },
    'ELECTRONS': {
        'conv_thr': 1.e-6,
        'electron_maxstep ': 100,
        'mixing_mode': 'plain',
        'mixing_beta': 0.3,
    }
}

pw_nscf_parameters = {
    'CONTROL': {
        'calculation': 'nscf',
        'restart_mode': 'restart',
        'wf_collect': True,
        'tprnfor': True,
        'etot_conv_thr': 0.00001,
        'forc_conv_thr': 0.0001,
        'verbosity': 'high',
    },
    'SYSTEM': {
        'ecutwfc': 20.,
        'nbnd': 80,
        'force_symmorphic': True,
    },
    'ELECTRONS': {
        'conv_thr': 1.e-6,
        'electron_maxstep ': 100,
        'mixing_mode': 'plain',
        'mixing_beta': 0.3,
    }
}

yambo_parameters = {
    'ppa': True,
    'gw0': True,
    'HF_and_locXC': True,
    'NLogCPUs': 0,
    'em1d': True,
    'X_all_q_nCPU_invert': 0,
    'X_Threads': 0,
    'DIP_Threads': 0,
    'SE_Threads': 2,
    'NGsBlkXp': 1,
    'NGsBlkXp_units': 'RL',
    'PPAPntXp': 10,
    'PPAPntXp_units': 'eV',
    'GDamping': 0.1,
    'GDamping_units': 'eV',
    'dScStep': 0.1,
    'dScStep_units': 'eV',
    'GTermKind': "none",
    'DysSolver': "n",
    'QPkrange': [(1, 4, 2, 6)],
}

calculation_set_pw = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2
    },
    'max_wallclock_seconds': 3 * 60 * 60,
    'max_memory_kb':
    1 * 86 * 1000000,  #'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
}

calculation_set_p2y = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1
    },
    'max_wallclock_seconds': 60 * 29,
    'max_memory_kb':
    1 * 86 * 1000000,  # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
}

calculation_set_yambo = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2
    },
    'max_wallclock_seconds': 3 * 60 * 60,
    'max_memory_kb':
    1 * 86 * 1000000,  # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
    'environment_variables': {
        "OMP_NUM_THREADS": "1"
    }
}

settings_pw = ParameterData(dict={})

settings_p2y = ParameterData(
    dict={
        "ADDITIONAL_RETRIEVE_LIST": [
            'r-*', 'o-*', 'l-*', 'l_*', 'LOG/l-*_CPU_1', 'aiida/ndb.QP',
            'aiida/ndb.HF_and_locXC'
        ],
        'INITIALISE':
        True
    })

settings_yambo = ParameterData(
    dict={
        "ADDITIONAL_RETRIEVE_LIST": [
            'r-*', 'o-*', 'l-*', 'l_*', 'LOG/l-*_CPU_1', 'aiida/ndb.QP',
            'aiida/ndb.HF_and_locXC'
        ],
        'INITIALISE':
        False
    })

KpointsData = DataFactory("array.kpoints")

#distance_kpoints = 0.34816 # 25% change
distance_kpoints = 0.2109375  # 25% change
kpoints = KpointsData()
kpoints.set_cell_from_structure(struc)
kpoints.set_kpoints_mesh_from_density(
    distance=distance_kpoints, force_parity=False)

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
        "calculation_set_pw": ParameterData(dict=calculation_set_pw),
        "calculation_set_p2y": ParameterData(dict=calculation_set_p2y),
        "calculation_set_yambo": ParameterData(dict=calculation_set_yambo),
        "settings_pw": settings_pw,
        "settings_p2y": settings_p2y,
        "settings_yambo": settings_yambo,
        "input_pw": ParameterData(dict={}),
        "structure": structure,
        "kpoint_pw": kpoints,
        "gamma_pw": Bool(False),
        "parameters_pw": ParameterData(dict=pw_parameters),
        "parameters_pw_nscf": ParameterData(dict=pw_nscf_parameters),
        "parameters_p2y": ParameterData(dict=yambo_parameters),
        "parameters_yambo": ParameterData(dict=yambo_parameters),
    }
    if parent_calc:
        kwargs["parent_folder"] = parent_calc.out.remote_folder
    if args.parent_workchain:
        kwargs["previous_yambo_workchain"] = Str(args.parent_workchain)
    full_result = run(YamboWorkflow, **kwargs)
    print(("Workflow submited :", full_result))
