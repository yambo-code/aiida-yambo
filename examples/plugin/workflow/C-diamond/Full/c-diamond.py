from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

from aiida_yambo.workflows.gwconvergence  import  YamboFullConvergenceWorkflow
from aiida.orm.data.base import Float, Str, NumericType, BaseType, List
from aiida.work.run import run, submit
from aiida.orm.utils import DataFactory
ParameterData = DataFactory("parameter")
StructureData = DataFactory('structure')


from ase.spacegroup import crystal
a=3.567
cell = crystal('C', [(0,0,0)], spacegroup=227, cellpar=[a, a, a, 90, 90, 90],primitive_cell=True)
struc = StructureData(ase=cell)

struc.store()


calculation_set_yambo ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 2}, 'max_wallclock_seconds': 60*60/2 ,
                  'max_memory_kb': 1*80*1000000 , # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n",
                  'environment_variables': {"omp_num_threads": "0" }  }
calculation_set_pw ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 2 }, 'max_wallclock_seconds': 60*45,
                  'max_memory_kb': 1*80*1000000 ,  # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622\n",
                  'environment_variables': {"omp_num_threads": "0" }  }


if __name__ == "__main__":
    # verdi run test_gwco.py --precode p2h@hyd   --yambocode yamb@hyd  --pwcode qe6.1@hyd --pseudo CHtest  --parent  637
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
    parser.add_argument('--parent', type=int, dest='parent', required=False,
                        help='The parent SCF   to use')

    threshold = Float(0.05)
    args = parser.parse_args()
    structure =  struc
    extra={}
    if  args.parent:
        parent = load_node(args.parent)
        extra['parent_scf_folder'] = parent.out.remote_folder
    p2y_result =submit(YamboFullConvergenceWorkflow, 
                    pwcode= Str( args.pwcode), 
                    precode= Str( args.precode), 
                    pseudo= Str( args.pseudo), 
                    yambocode=Str(args.yambocode),
                    structure=structure,
                    calculation_set= ParameterData(dict=calculation_set_yambo),
                    calculation_set_pw= ParameterData(dict=calculation_set_pw),
                    threshold = threshold, 
                     **extra
                    )
    print ("Wf launched", p2y_result)
