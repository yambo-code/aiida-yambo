from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.yambowf  import YamboWorkflow
 
try:
    from aiida.orm.data.base import Float, Str, NumericType, BaseType, Bool, List  
    from aiida.work.run import run, submit
except ImportError:
    from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData, Bool
    from aiida.workflows2.db_types import  SimpleData as BaseType
    from aiida.orm.data.simple import  SimpleData as SimpleData_
    from aiida.workflows2.run import run

from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')

cell = [[4.2262023163, 0.0000000000, 0.0000000000],
        [0.0000000000, 4.2262023163, 0.0000000000],
        [0.0000000000, 0.0000000000, 2.7009939524],
       ]
struc = StructureData(cell=cell)
struc.append_atom(position=(1.2610450495  ,1.2610450495  ,0.0000000000  ), symbols='O')
struc.append_atom(position=(0.8520622471  ,3.3741400691  ,1.3504969762  ), symbols='O')
struc.append_atom(position=(2.9651572668  ,2.9651572668  ,0.0000000000  ), symbols='O')
struc.append_atom(position=(3.3741400691  ,0.8520622471  ,1.3504969762  ), symbols='O')
struc.append_atom(position=( 0.0000000000 , 0.0000000000 , 0.0000000000 ), symbols='Ti')
struc.append_atom(position=( 2.1131011581 , 2.1131011581 , 1.3504969762 ), symbols='Ti')

struc.store()

pw_parameters =  {
          'CONTROL': {
              'calculation': 'scf',
              'restart_mode': 'from_scratch',
              'wf_collect': True,
              'tprnfor': True,
              'etot_conv_thr': 0.00001,
              'forc_conv_thr': 0.0001,
              'verbosity' :'high',
              },
          'SYSTEM': {
              'ecutwfc': 35.,
              },
          'ELECTRONS': {
              'conv_thr': 1.e-8,
              'electron_maxstep ': 100,
              'mixing_mode': 'plain',
              'mixing_beta' : 0.3,
              } } 

pw_nscf_parameters =  {
          'CONTROL': {
              'calculation': 'nscf',
              'restart_mode': 'from_scratch',
              'wf_collect': True,
              'tprnfor': True,
              'etot_conv_thr': 0.00001,
              'forc_conv_thr': 0.0001,
              'verbosity' :'high',
              },
          'SYSTEM': {
              'ecutwfc': 35.,
              'nbnd':40,
              'force_symmorphic': True,
              },
          'ELECTRONS': {
              'conv_thr': 1.e-8,
              'electron_maxstep ': 100,
              'mixing_mode': 'plain',
              'mixing_beta' : 0.3,
              } } 


yambo_parameters = {'ppa': True,
                                 'gw0': True,
                                 'HF_and_locXC': True,
                                 'NLogCPUs': 0,
                                 'em1d': True,
                                 #'X_all_q_CPU': "1 1 16 8",
                                 #'X_all_q_ROLEs': "q k c v",
                                 'X_all_q_nCPU_invert':0,
                                 'X_Threads':  0 ,
                                 'DIP_Threads': 0 ,
                                 #'SE_CPU': "1 8 16",
                                 #'SE_ROLEs': "q qp b",
                                 'SE_Threads':  32,
                                 'EXXRLvcs': 789569,
                                 'EXXRLvcs_units': 'RL',
                                 'BndsRnXp': (1,38),
                                 'NGsBlkXp': 3,
                                 'NGsBlkXp_units': 'Ry',
                                 'PPAPntXp': 2000000,
                                 'PPAPntXp_units': 'eV',
                                 'GbndRnge': (1,38),
                                 'GDamping': 0.1,
                                 'GDamping_units': 'eV',
                                 'dScStep': 0.1,
                                 'dScStep_units': 'eV',
                                 'GTermKind': "none",
                                 'DysSolver': "n",
                                 'QPkrange': [(1,8,34,38)],
                                 }

calculation_set_pw ={'resources':  {"num_machines": 4,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds': 3*60*60, 
                  'max_memory_kb': 1*86*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }

calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
                  'max_memory_kb': 1*86*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "1" }  }

calculation_set_yambo ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds': 3*60*60, 
                  'max_memory_kb': 1*86*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }

#calculation_set_pw ={'resources':  {"num_machines": 2,"num_mpiprocs_per_machine":  16}, 'max_wallclock_seconds': 3*60*60, 
#                  'max_memory_kb': 1*92*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n#PBS -q s3par8cv3" ,
#                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }

#calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
#                  'max_memory_kb': 1*92*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n#PBS -q s3par8cv3" ,
#                  'environment_variables': {"OMP_NUM_THREADS": "1" }  }

#calculation_set_yambo ={'resources':  {"num_machines": 2,"num_mpiprocs_per_machine": 16}, 'max_wallclock_seconds': 200, 
#                  'max_memory_kb': 1*92*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n#PBS -q s3par8cv3" ,
#                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }


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
    parser.add_argument('--structure', type=int, dest='structure', required=False,
                        help='The structure  to use')
    parser.add_argument('--parent', type=int, dest='parent', required=False,
                        help='QE scf/nscf calculation ')

    args = parser.parse_args()
    if not args.structure:
        structure = struc
    else:
        structure = load_node(int(args.structure)) #1791 
    parent_calc = None
    if args.parent:
        parent_calc = load_node(int(args.parent)) #1791 
    kwargs = {     "codename_pw": Str(args.pwcode),
                   "codename_p2y":Str( args.precode),
                   "codename_yambo": Str(args.yambocode),
                   "pseudo_family": Str(args.pseudo),
                   "calculation_set_pw" :ParameterData(dict=calculation_set_pw ),
                   "calculation_set_p2y" :ParameterData(dict=calculation_set_p2y) ,
                   "calculation_set_yambo" :ParameterData(dict= calculation_set_yambo ),
                   "settings_pw" :settings_pw ,
                   "settings_p2y" :settings_p2y ,
                   "settings_yambo":settings_yambo ,
                   "input_pw" : ParameterData(dict={}), 
                   "structure" : structure,
                   "kpoint_pw" : kpoints,
                   "gamma_pw" : Bool(False),
                   "parameters_pw" : ParameterData(dict=pw_parameters) , 
                   "parameters_pw_nscf" : ParameterData(dict=pw_nscf_parameters) , 
                   "parameters_p2y" : ParameterData(dict=yambo_parameters) ,
                   "parameters_yambo" : ParameterData(dict=yambo_parameters),  
          }
    if parent_calc:
          kwargs["parent_folder"] =  parent_calc.out.remote_folder
    full_result = submit(YamboWorkflow, **kwargs )
    print ("Resutls", full_result)
