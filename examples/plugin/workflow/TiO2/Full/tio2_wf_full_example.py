from __future__ import absolute_import
from __future__ import print_function
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.gwconvergence import YamboFullConvergenceWorkflow
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.work.run import run, submit
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')

cell = [
    [4.6313377290, 0.0000000000, 0.0000000000],
    [0.0000000000, 4.6313377290, 0.0000000000],
    [0.0000000000, 0.0000000000, 2.9599186840],
]
struc = StructureData(cell=cell)
struc.append_atom(
    position=(1.4128030100, 1.4128030100, 0.0000000000), symbols='O')
struc.append_atom(
    position=(0.9028658550, 3.7284718740, 1.4799593420), symbols='O')
struc.append_atom(
    position=(3.2185347190, 3.2185347190, 0.0000000000), symbols='O')
struc.append_atom(
    position=(3.7284718740, 0.9028658550, 1.4799593420), symbols='O')
struc.append_atom(
    position=(0.0000000000, 0.0000000000, 0.0000000000), symbols='Ti')
struc.append_atom(
    position=(2.3156688650, 2.3156688650, 1.4799593420), symbols='Ti')
struc.store()

calculation_set_yambo = {
    'resources': {
        "num_machines": 2,
        "num_mpiprocs_per_machine": 16
    },
    'max_wallclock_seconds': 59 * 60 * 20,
    'max_memory_kb': 1 * 80 * 1000000,
    'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n",
    "queue_name": "s3par8c",
    'environment_variables': {
        "omp_num_threads": "0"
    }
}
calculation_set_pw = {
    'resources': {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 16
    },
    'max_wallclock_seconds': 60 * 60 * 12,
    'max_memory_kb': 1 * 80 * 1000000,
    'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n",
    "queue_name": "s3par8c",
    'environment_variables': {
        "omp_num_threads": "0"
    }
}
convergence_settings = ParameterData(
    dict={
        'start_fft': 48,
        'max_fft': 200,
        'start_bands': 288,
        'max_bands': 4000,
        'start_w_cutoff': 2,
        'max_w_cutoff': 40,
        'kpoint_starting_distance': .35,
        'kpoint_min_distance': 0.025
    })

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
        '--parent',
        type=int,
        dest='parent',
        required=False,
        help='The parent SCF   to use')

    threshold = Float(0.1)
    args = parser.parse_args()
    structure = struc
    extra = {}
    if args.parent:
        parent = load_node(args.parent)
        extra['parent_scf_folder'] = parent.out.remote_folder
    p2y_result = submit(
        YamboFullConvergenceWorkflow,
        pwcode=Str(args.pwcode),
        precode=Str(args.precode),
        pseudo=Str(args.pseudo),
        yambocode=Str(args.yambocode),
        structure=structure,
        calculation_set=ParameterData(dict=calculation_set_yambo),
        calculation_set_pw=ParameterData(dict=calculation_set_pw),
        convergence_settings=convergence_settings,
        threshold=threshold,
        **extra)
    print(("Wf launched", p2y_result))
