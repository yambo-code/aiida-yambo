from aiida.backends.utils import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()
import json
import os, sys
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
KpointsData = DataFactory('array.kpoints')

def read_from_pw_inp(filename="../GS/nscf.in"):
    from aiida_quantumespresso.tools import pwinputparser
    pwinputfile = pwinputparser.PwInputFile(os.path.abspath(filename))
    struc =  pwinputfile.get_structuredata()
    pw_params = pwinputfile.namelists  # CONTROL, SYSTEM, ELECTRONS,...
    control = pw_params['CONTROL']
    system = pw_params['SYSTEM']
    del control['pseudo_dir']
    del control['outdir']
    del control['prefix']
    pw_params['CONTROL'] = control
    del system['ibrav']
    del system['celldm(1)']
    del system['celldm(2)']
    del system['celldm(3)']
    del system['nat']
    del system['ntyp']
    pw_params['SYSTEM'] = system
    k_points = pwinputfile.k_points
    return (pw_params, struc, k_points)

def read_yambo_json(filename="../INPUTS/init_01.json"):
    with open(filename, 'r') as content:
        y_config = json.loads(content.read())
    return y_config
##TODO struc
##TODO pw_params
pw_parameters = ParameterData(dict={})
pw_nscf_parameters =ParameterData(dict={})
##TODO yambo params
yambo_parameters = ParameterData(dict={})


calculation_set_pw ={'resources':  {"num_machines": 2,"num_mpiprocs_per_machine": 16}, 'max_wallclock_seconds': 3*60*60, 
        'max_memory_kb': 1*86*1000000 , 'custom_scheduler_commands': u"#SBATCH --account=Pra14_3622\n#SBATCH --partition=knl_usr_prod",
                  'environment_variables': {"OMP_NUM_THREADS": "1" }  }

calculation_set_p2y ={'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 1}, 'max_wallclock_seconds':  60*29, 
        'max_memory_kb': 1*86*1000000 , 'custom_scheduler_commands': u"#SBATCH --account=Pra14_3622\n#SBATCH --partition=knl_usr_prod",
                  'environment_variables': {"OMP_NUM_THREADS": "1" }  }

calculation_set_yambo ={'resources':  {"num_machines": 2,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds': 3*60*60, 
        'max_memory_kb': 1*86*1000000 , 'custom_scheduler_commands': u"#SBATCH --account=Pra14_3622\n#SBATCH --partition=knl_usr_prod",
                  'environment_variables': {"OMP_NUM_THREADS": "2" }  }

settings_pw =  ParameterData(dict= {})

settings_p2y =   ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':True})

settings_yambo =  ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':False })


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
                        help='QE scf/nscf / yambo calculation ')
    parser.add_argument('--parent-workchain', type=int, dest='parent_workchain', required=False,
                        help=' Parent yambo workflow ')
    parser.add_argument('--scfinput', type=str, dest='scfinput', required=False,
                        help=' prexisitng inputfile to parse for parameters, structure and kpoints ')
    parser.add_argument('--nscfinput', type=str, dest='nscfinput', required=False,
                        help=' prexisitng inputfile to parse for parameters, structure and kpoints ')
    parser.add_argument('--yamboconfig', type=str, dest='yamboconfig', required=False,
                        help=' prexisitng inputfile to parse for parameters, structure and kpoints ')
    args = parser.parse_args()
    structure = None
    kpoints = None
    if not args.structure:
        if args.scfinput:
            pw_parameters , structure, kpoints =  read_from_pw_inp(filename=args.scfinput)
        if args.nscfinput:
            pw_nscf_parameters, structure, kpoints =  read_from_pw_inp(filename=args.scfinput)
    else:
        structure = load_node(int(args.structure)) #1791 
    if structure is None and not args.parent:
        print("provide a structure if not starting from p2y/yambo")
        sys.exit(1)
    if kpoints: # assuming kpoints == automatic 
        kpt = KpointsData()
        kpt.set_kpoints_mesh( kpoints['points'], offset=kpoints['offset'])
        kpoints= kpt
    parent_calc = None
    if args.parent:
        parent_calc = load_node(int(args.parent)) #1791 
    if args.yamboconfig:
        yambo_parameters = read_yambo_json(filename=args.yamboconfig)    
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
    if args.parent_workchain:
          kwargs["previous_yambo_workchain"] =  Str(args.parent_workchain)
    full_result = run(YamboWorkflow, **kwargs )
    print ("Workflow submited :", full_result)
