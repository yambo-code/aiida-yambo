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

StructureData = DataFactory('structure')

cell = [[5.3976054000,    0.0000000000,    0.0000000000 ],
        [0.0000000000,    5.3976054000,    0.0000000000 ],
        [0.0000000000,    0.0000000000,    5.3976054000 ],
       ]
struc = StructureData(cell=cell)
struc.append_atom(position=( 2.6988027000,     2.6988027000,     0.0000000000), symbols='Si')
struc.append_atom(position=( 0.0000000000,     0.0000000000,     0.0000000000), symbols='Si')
struc.append_atom(position=( 2.6988027000,     0.0000000000,     2.6988027000), symbols='Si')
struc.append_atom(position=( 0.0000000000,     2.6988027000,     2.6988027000), symbols='Si')
struc.append_atom(position=( 4.0482040500,     4.0482040500,     1.3494013500), symbols='Si')
struc.append_atom(position=( 1.3494013500,     1.3494013500,     1.3494013500), symbols='Si')
struc.append_atom(position=( 4.0482040500,     1.3494013500,     4.0482040500), symbols='Si')
struc.append_atom(position=( 1.3494013500,     4.0482040500,     4.0482040500), symbols='Si')

struc.store()

calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
                  'max_memory_kb': 1*80*1000000 , 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"omp_num_threads": "1" }  }

calculation_set_yambo ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds':  2*60*60, 
                  'max_memory_kb': 1*80*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"omp_num_threads": "16" }  }

calculation_set_pw ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds':  1*60*60, 
                  'max_memory_kb': 1*80*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"omp_num_threads": "16" }  }



convergence_parameters = DataFactory('parameter')(dict= { 
                           'variable_to_converge': 'kpoints', 'conv_tol':0.1, 
                            'start_value': .9  , 'step':.1 , 'max_value': 0.017 })

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
                        help='The pseudo  to use')
    parser.add_argument('--parent', type=int, dest='parent', required=True,
                        help='The parent  to use')
    parser.add_argument('--parent_nscf', type=int, dest='parent_nscf', required=True,
                        help='The parent nscf  to use')

    args = parser.parse_args()
    structure =  struc
    p2y_result =submit(YamboConvergenceWorkflow, 
                    pwcode= Str(args.pwcode),
                    precode= Str( args.precode), 
                    yambocode=Str(args.yambocode),
                    calculation_set= ParameterData(dict=calculation_set_yambo),
                    calculation_set_pw= ParameterData(dict=calculation_set_pw),
                    convergence_parameters=ParameterData(dict=convergence_parameters),
                    structure = structure , 
                    pseudo = Str(args.pseudo),
                    )

    print ("Workflow launched", p2y_result)
