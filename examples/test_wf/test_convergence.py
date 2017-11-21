from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.yamboconvergence  import  YamboConvergenceWorkflow
 
try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
    from aiida.work.run import run, submit
except ImportError:
    from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData, Bool
    from aiida.workflows2.db_types import  SimpleData as BaseType
    from aiida.orm.data.simple import  SimpleData as SimpleData_
    from aiida.workflows2.run import run

from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")

yambo_parameters = {'ppa': True,
                                 'gw0': True,
                                 'HF_and_locXC': True,
                                 'em1d': True,
                                 'DIP_Threads': 0 ,
                                 'BndsRnXp': (1,16),
                                 'NGsBlkXp': 1,
                                 'NGsBlkXp_units': 'RL',
                                 'PPAPntXp': 20,
                                 'PPAPntXp_units': 'eV',
                                 'GbndRnge': (1,16),
                                 'GDamping': 0.1,
                                 'GDamping_units': 'eV',
                                 'dScStep': 0.1,
                                 'dScStep_units': 'eV',
                                 'DysSolver': "n",
                                 'QPkrange': [(1,1,16,18)],
                                 }


calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
                  'max_memory_kb': 1*80*1000000 ,"queue_name":"s3par8cv3" ,#'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"omp_num_threads": "1" }  }

calculation_set_yambo ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 16}, 'max_wallclock_seconds':  6*60*60, 
                  'max_memory_kb': 1*80*1000000 , "queue_name":"s3par8cv3" ,#'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"omp_num_threads": "0" }  }

settings_pw =  ParameterData(dict= {'cmdline':['-npool', '2' , '-ndiag', '8', '-ntg', '2' ]})

settings_p2y =   ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':True})

settings_yambo =  ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':False })



KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData()
kpoints.set_kpoints_mesh([2,2,2])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='GW QP calculation.')
    parser.add_argument('--precode', type=str, dest='precode', required=True,
                        help='The p2y codename to use')
    parser.add_argument('--yambocode', type=str, dest='yambocode', required=True,
                        help='The yambo codename to use')

    parser.add_argument('--pwcode', type=str, dest='pwcode', required=True,
                        help='The pw codename to use')
    parser.add_argument('--pseudo', type=str, dest='pseudo', required=True,
                        help='The pesudo  to use')
    parser.add_argument('--structure', type=int, dest='structure', required=True,
                        help='The structure  to use')
    parser.add_argument('--parent', type=int, dest='parent', required=False,
                        help='The parent  to use')
    parser.add_argument('--parent_nscf', type=int, dest='parent_nscf', required=False,
                        help='The parent nscf  to use')

    args = parser.parse_args()
    structure = load_node(int(args.structure))
    parentcalc = parent_folder_ = parentnscfcalc = parent_nscf_folder_ = False
    if args.parent:
        parentcalc = load_node(int(args.parent))
        parent_folder_ = parentcalc.out.remote_folder
        parentnscfcalc = load_node(int(args.parent_nscf))
        parent_nscf_folder_ = parentnscfcalc.out.remote_folder
    convergence_parameters = {'variable_to_converge': 'kpoints', 'conv_tol':0.1,
                                   'start_value': .9  , 'step':.1 , 'max_value': 0.017 }
    p2y_result =run(YamboConvergenceWorkflow, 
                    pwcode= Str( args.pwcode), 
                    precode= Str( args.precode), 
                    yambocode=Str(args.yambocode),
                    calculation_set= ParameterData(dict=calculation_set_yambo),
                    settings = settings_yambo,
                    convergence_parameters = ParameterData(dict=convergence_parameters),
                    #parent_scf_folder = parent_folder_, 
                    #parent_nscf_folder = parent_nscf_folder_, 
                    parameters = ParameterData(dict=yambo_parameters), 
                    structure = structure , 
                    pseudo = Str(args.pseudo),
                    )

    print ("Workflow launched: ", p2y_result)
