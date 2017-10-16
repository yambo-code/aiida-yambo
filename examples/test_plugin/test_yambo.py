from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida.workflows.user.cnr_nano.yamborestart  import YamboRestartWf
 
try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType
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
                                 'NLogCPUs': 0,
                                 'em1d': True,
                                 'X_all_q_CPU': "",
                                 'X_all_q_ROLEs': "",
                                 'X_all_q_nCPU_invert':0,
                                 'X_Threads':  0 ,
                                 'DIP_Threads': 0 ,
                                 'SE_CPU': "",
                                 'SE_ROLEs': "",
                                 'SE_Threads':  32,
                                 'EXXRLvcs': 789569,
                                 'EXXRLvcs_units': 'RL',
                                 'BndsRnXp': (1,60),
                                 'NGsBlkXp': 3,
                                 'NGsBlkXp_units': 'Ry',
                                 'PPAPntXp': 2000000,
                                 'PPAPntXp_units': 'eV',
                                 'GbndRnge': (1,60),
                                 'GDamping': 0.1,
                                 'GDamping_units': 'eV',
                                 'dScStep': 0.1,
                                 'dScStep_units': 'eV',
                                 'GTermKind': "none",
                                 'DysSolver': "n",
                                 'QPkrange': [(1,16,30,31)],
                                 }


calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
                  'max_memory_kb': 1*88*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "1" }  }

calculation_set_yambo ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds':  60*60, 
                  'max_memory_kb': 1*10*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }

settings_pw =  ParameterData(dict= {'cmdline':['-npool', '2' , '-ndiag', '8', '-ntg', '2' ]})

settings_p2y =   ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':True})

settings_yambo =  ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'] })



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
    parser.add_argument('--parent', type=int, dest='parent', required=True,
                        help='The parent  to use')

    args = parser.parse_args()
    structure = load_node(int(args.structure))
    parentcalc = load_node(int(args.parent))
    parent_folder_ = parentcalc.out.remote_folder
    p2y_result =run(YamboRestartWf, 
                    precode= Str( args.precode), 
                    yambocode=Str(args.yambocode),
                    parameters = ParameterData(dict=yambo_parameters) , 
                    calculation_set= ParameterData(dict=calculation_set_yambo),
                    parent_folder = parent_folder_, settings = settings_yambo)

    print ("Resutls", p2y_result)
