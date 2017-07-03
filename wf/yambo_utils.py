import sys
import copy
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.common.exceptions import InputValidationError,ValidationError, WorkflowInputValidationError
from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from collections import defaultdict
from aiida.orm.utils import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.orm.calculation.job.yambo  import YamboCalculation
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation

ParameterData = DataFactory("parameter")


def generate_yambo_input_params(precodename,yambocodename, parent_folder, parameters,  calculation_set, settings):
    inputs = YamboCalculation.process().get_inputs_template()
    inputs.preprocessing_code = Code.get_from_string(precodename.value)
    inputs.code = Code.get_from_string(yambocodename.value)
    calculation_set = calculation_set.get_dict()
    resource = calculation_set.pop('resources', {})
    if resource:
        inputs._options.resources =  resource 
    inputs._options.max_wallclock_seconds =  calculation_set.pop('max_wallclock_seconds', 86400) 
    max_memory_kb = calculation_set.pop('max_memory_kb',None)
    if max_memory_kb:
        inputs._options.max_memory_kb = max_memory_kb
    queue_name = calculation_set.pop('queue_name',None)
    if queue_name:
        inputs._options.queue_name = queue_name 
    custom_scheduler_commands = calculation_set.pop('custom_scheduler_commands',None)
    if custom_scheduler_commands:
        inputs._options.custom_scheduler_commands = custom_scheduler_commands
    environment_variables = calculation_set.pop("environment_variables",None)
    if environment_variables:
        inputs._options.environment_variables = environment_variables
    label = calculation_set.pop('label',None)
    if label:
        inputs._label = label 
    inputs.parameters = parameters
    inputs.parent_folder = parent_folder
    inputs.settings =  settings 
    #inputs.settings =  ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
    #              'r-*','o-*','l-*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC']})
    return  inputs

def get_pseudo(structure, pseudo_family):
    kind_pseudo_dict = get_pseudos_from_structure(structure, pseudo_family)
    pseudo_dict = {}
    pseudo_species = defaultdict(list)
    for kindname, pseudo in kind_pseudo_dict.iteritems():
        pseudo_dict[pseudo.pk] = pseudo
        pseudo_species[pseudo.pk].append(kindname)
    pseudos = {}
    for pseudo_pk in pseudo_dict:
        pseudo = pseudo_dict[pseudo_pk]
        kinds = pseudo_species[pseudo_pk]
        for kind in kinds:
            pseudos[kind] = pseudo
    return pseudos


def generate_pw_input_params(structure, codename, pseudo_family,parameters, calculation_set, kpoints,gamma,settings,parent_folder):
    """
    inputs_template: {'code': None, 'vdw_table': None, 'parameters': None, 
                      '_options': DictSchemaInputs({'resources': DictSchemaInputs({})}), 
                      'kpoints': None, 'settings': None, 'pseudo': None, 
                      'parent_folder': None, 'structure': None}
    """
    inputs = PwCalculation.process().get_inputs_template()
    inputs.structure = structure
    inputs.code = Code.get_from_string(codename.value)
    calculation_set = calculation_set.get_dict() 
    resource = calculation_set.pop('resources', {})
    if resource:
        inputs._options.resources =  resource
    inputs._options.max_wallclock_seconds =  calculation_set.pop('max_wallclock_seconds', 86400) 
    max_memory_kb = calculation_set.pop('max_memory_kb',None)
    if max_memory_kb:
        inputs._options.max_memory_kb = max_memory_kb
    queue_name = calculation_set.pop('queue_name',None)
    if queue_name:
        inputs._options.queue_name = queue_name           
    custom_scheduler_commands = calculation_set.pop('custom_scheduler_commands',None)
    if custom_scheduler_commands:
        inputs._options.custom_scheduler_commands = custom_scheduler_commands
    environment_variables = calculation_set.pop("environment_variables",None)
    if environment_variables:
        inputs._options.environment_variables = environment_variables
    label = calculation_set.pop('label',None)
    if label :
        inputs._label = label
    if parent_folder:
        inputs.parent_folder = parent_folder
        print("parent folder set")
    inputs.kpoints=kpoints
    inputs.parameters = parameters  
    inputs.pseudo = get_pseudo(structure, str(pseudo_family))
    inputs.settings  = settings
    #if gamma:
    #    inputs.settings = ParameterData(dict={'gamma_only':True})
    return  inputs


def reduce_parallelism(typ, roles,  values,calc_set):
    """
                        X_all_q_CPU = params.pop('X_all_q_CPU','')
                        X_all_q_ROLEs =  params.pop('X_all_q_ROLEs','')
                        SE_CPU = params.pop('SE_CPU','')
                        SE_ROLEs = params.pop('SE_ROLEs','')
                        calculation_set_yambo ={'resources':  {"num_machines": 8,"num_mpiprocs_per_machine": 32}, 'max_wallclock_seconds': 200,
                             'max_memory_kb': 1*92*1000000 ,  'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                             '  environment_variables': {"OMP_NUM_THREADS": "2" }  
                             }
    """
    calculation_set = copy.deepcopy(calc_set)
    # the latter needs to be reduced, we can either increase the former or leave it untouched.
    # lets reduce it by  50% if its >=2, else increase num_machines, holding it constant at 1
    num_machines = calculation_set['resources']['num_machines']    
    num_mpiprocs_per_machine = calculation_set['resources']['num_mpiprocs_per_machine']
    omp_threads=1
    if 'environment_variables' in calculation_set.keys():
        omp_threads = calculation_set['environment_variables'].pop('OMP_NUM_THREADS',1)
    num_mpiprocs_per_machine=int(num_mpiprocs_per_machine/2)
    omp_threads= omp_threads*2 
    if num_mpiprocs_per_machine < 1:
        num_mpiprocs_per_machine = 1 
        num_machines = num_machines * 2
    calculation_set['environment_variables']['OMP_NUM_THREADS'] = omp_threads
    calculation_set['environment_variables']['NUM_CORES_PER_MPIPROC'] = omp_threads
    # adjust the X_all_q_CPU and SE_CPU
    mpi_task = num_mpiprocs_per_machine*num_machines 
    if typ == 'X_all_q_CPU':
        #X_all_q_CPU = "1 1 96 32"
        #X_all_q_ROLEs = "q k c v"
        X_para = [ int(it) for it in values.strip().split(' ') if it ]
        try:
            c_index = roles.strip().split(' ').index("c")
            v_index = roles.strip().split(' ').index("v")
            c = X_para[c_index] or 1
            v = X_para[v_index] or 1
        except ValueError:
            c_index = v_index = 0
            c = 1
            v = 1
        if c_index and v_index:
            pass
        if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and v >1:
            v = v/2 
        if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and v == 1:
            c = c/2 
        if num_machines > calculation_set['resources']['num_machines']: 
            c = c*2 
        if c_index and v_index:
            X_para[c_index] = c  
            X_para[v_index] = v
        X_string = " ".join([str(it) for it in X_para])
        calculation_set['resources']['num_machines'] = num_machines
        calculation_set['resources']['num_mpiprocs_per_machine'] = num_mpiprocs_per_machine
        if c_index and v_index:
            pass
        return X_string , calculation_set
            
    if typ == 'SE_CPU':
        #SE_ROLEs = "q qp b"
        #SE_CPU = "1 32 96"
        SE_para  = [ int(it) for it in values.strip().split(' ') if it ]
        try:
            qp_index = roles.strip().split(' ').index("qp")
            b_index = roles.strip().split(' ').index("b")
            qp = SE_para[qp_index] or  1
            b  = SE_para[b_index] or 1  
        except ValueError:
            qp_index = b_index = 0
            qp =1
            b  =1  
        if qp_index and b_index: 
            pass
        if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and qp >1:
             qp = qp/2 
        if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and qp == 1:
            qp = qp/2 
        if num_machines > calculation_set['resources']['num_machines']: 
            b = b*2 
        if qp_index and b_index: 
            SE_para[qp_index] = qp  
            SE_para[b_index] = b
        SE_string = " ".join([str(it) for it in SE_para])
        calculation_set['resources']['num_machines'] = num_machines
        calculation_set['resources']['num_mpiprocs_per_machine'] = num_mpiprocs_per_machine
        if qp_index and b_index: 
            pass
        return SE_string, calculation_set
   

"""
  - BndsRnXp 
  - GbndRnge   
  - BSEBands 
  - PPAPntXp [OK]
  - NGsBlkXp [OK]
  - BSENGBlk [OK]
  - BSENGexx [OK]
"""
default_step_size = {
               'PPAPntXp': .2,   
               'NGsBlkXp': .1,   
               'BSENGBlk': .1,  
               'BSENGexx': .2,
               'BndsRnXp': .2, 
               'GbndRnge': .2,
               'BSEBands': 2, # 
                }

def update_parameter_field( field, starting_point, update_delta):
    if update_delta < 2:
       update_delta = 2 
    if field in ['PPAPntXp','NGsBlkXp','BSENGBlk','BSENGexx']: # single numbers
        new_field_value =  starting_point  + update_delta 
        return new_field_value
    elif field == 'BndsRnXp':
        new_field_value =  starting_point[-1]  + update_delta 
        return (1, new_field_value)
    elif field == 'GbndRnge':
        new_field_value =  starting_point[-1]  + update_delta 
        return (1, new_field_value)
    elif field == 'BSEBands':  # Will be useful when we support BSE calculations
        hi =  starting_point[-1] +   2
        low  =  starting_point[0]  -  2
        return ( low, hi )
    else:
        raise WorkflowInputValidationError("convergences the field {} are not supported".format(field))

