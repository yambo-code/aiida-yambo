import sys
import copy
from aiida.backends.utils import load_dbenv, is_dbenv_loaded
import math 

if not is_dbenv_loaded():
    load_dbenv()

from aiida.common.exceptions import InputValidationError,ValidationError, WorkflowInputValidationError
from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from collections import defaultdict
from aiida.orm.utils import DataFactory, CalculationFactory
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.common.links import LinkType
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_yambo.calculations.gw  import YamboCalculation

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
    inputs.parent_folder = parent_folder
    inputs.settings =  settings 
    # Get defaults:
    edit_parameters = parameters.get_dict()
    try:
        calc = parent_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder'].inp.parent_calc_folder.get_inputs_dict()\
               ['remote_folder'].inp.parent_calc_folder.get_inputs_dict()['remote_folder']
    except AttributeError:
        calc = None
    is_pw = False
    if isinstance(calc,PwCalculation):
        is_pw = True
        nelec = calc.out.output_parameters.get_dict()['number_of_electrons']
        nocc = None
        if calc.out.output_parameters.get_dict()['lsda']== True or\
           calc.out.output_parameters.get_dict()['non_colinear_calculation'] == True:
           nocc = nelec/2 
        else:
           nocc = nelec/2
        bndsrnxp = gbndrnge = nocc 
        ngsblxpp = int(calc.out.output_parameters.get_dict()['wfc_cutoff']* 0.073498645/4 * 0.25)   # ev to ry then 1/4 
        #ngsblxpp =  2
        nkpts = calc.out.output_parameters.get_dict()['number_of_k_points']
        if not resource:
             resource = {"num_mpiprocs_per_machine": 8, "num_machines": 1} # safe trivial defaults
        tot_mpi =  resource[u'num_mpiprocs_per_machine'] * resource[u'num_machines']
        if 'FFTGvecs' not in edit_parameters.keys():
             edit_parameters['FFTGvecs'] =  20
             edit_parameters['FFTGvecs_units'] =  'Ry'
        if 'BndsRnXp' not in edit_parameters.keys():
             edit_parameters['BndsRnXp'] = (bndsrnxp/2 ,bndsrnxp/2+1 )
        if 'GbndRnge' not in edit_parameters.keys():
             edit_parameters['GbndRnge'] = (1.0, gbndrnge/2) 
        if 'NGsBlkXp' not in edit_parameters.keys():
             edit_parameters['NGsBlkXp'] = ngsblxpp
             edit_parameters['NGsBlkXp_units'] =  'Ry'
        if 'QPkrange' not in edit_parameters.keys():
             edit_parameters['QPkrange'] = [(1,1,int(nocc), int(nocc)+1 )] # To revisit 
        if 'SE_CPU' not in  edit_parameters.keys():
            b, qp = split_incom(tot_mpi)
            edit_parameters['SE_CPU'] ="1 {qp} {b}".format(qp=qp, b = b) 
            edit_parameters['SE_ROLEs']= "q qp b"
        if 'X_all_q_CPU' not in  edit_parameters.keys():
            c, v = split_incom(tot_mpi)
            edit_parameters['X_all_q_CPU']= "1 1 {c} {v}".format(c = c, v = v)
            edit_parameters['X_all_q_ROLEs'] ="q k c v"
    
    inputs.parameters = ParameterData(dict=edit_parameters) 
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
    """
    inputs = {}
    inputs['structure'] = structure
    inputs['code'] = Code.get_from_string(codename.value)
    calculation_set = calculation_set.get_dict() 
    inputs['options'] = ParameterData(dict=calculation_set)
    if parent_folder:
        inputs['parent_folder'] = parent_folder
    inputs['kpoints']=kpoints
    inputs['parameters'] = parameters  
    inputs['pseudo_family'] =  pseudo_family
    inputs['settings']  = settings
    return  inputs


def reduce_parallelism(typ, roles,  values,calc_set):
    """
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
    omp_threads= int(omp_threads)*2
    increased_mpi_task = False 
    if num_mpiprocs_per_machine < 1:
        num_mpiprocs_per_machine = 1 
        num_machines = num_machines * 2
        increased_mpi_task = True 
    calculation_set['environment_variables']['OMP_NUM_THREADS'] = str(omp_threads)
    calculation_set['environment_variables']['NUM_CORES_PER_MPIPROC'] = str(omp_threads)
    if isinstance(values,list):
        values = values[0]
    if isinstance(roles,list):
        roles = roles[0]
    # adjust the X_all_q_CPU and SE_CPU
    mpi_task = num_mpiprocs_per_machine*num_machines 
    if typ == 'X_all_q_CPU':
        print "this type"
        #X_all_q_CPU = "1 1 96 32"
        #X_all_q_ROLEs = "q k c v"
        X_para = [ int(it) for it in values.strip().split(' ') if it ]
        try:
            c_index = roles.split(' ').index("c")
            v_index = roles.split(' ').index("v")
            c = X_para[c_index] or 1
            v = X_para[v_index] or 1
        except ValueError:
            c_index = v_index = 0
            c = 1
            v = 1
        except IndexError:
            c_index = v_index = 0
            c = 1
            v = 1
        # we should keep c*v == mpi_task, with  c>v always
        # if increased_mpi_task we try a simple assignment
        # else, we factor again?  
        c, v = split_incom(mpi_task*2)
        if  False:
            if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] :
                print("num_mpiprocs_per_machine {} , calculation_set['resources']['num_mpiprocs_per_machine'] {}, v {}".format(
                      num_mpiprocs_per_machine, calculation_set['resources']['num_mpiprocs_per_machine'] , v ))
                print("num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and v == 1")
                c = c/2 
            if num_machines > calculation_set['resources']['num_machines']:
                print("num_machines {} , calculation_set['resources']['num_machines'] {},".format(
                      num_machines, calculation_set['resources']['num_machines']  ))
                print("num_machines > calculation_set['resources']['num_machines']")
                c = c*2 
        if False: 
            if num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and v >1:
                print("num_mpiprocs_per_machine {} , calculation_set['resources']['num_mpiprocs_per_machine'] {}, v {}".format(
                      num_mpiprocs_per_machine, calculation_set['resources']['num_mpiprocs_per_machine'] , v ))
                print("num_mpiprocs_per_machine < calculation_set['resources']['num_mpiprocs_per_machine'] and v >1")
                v = v/2 
            if num_machines > calculation_set['resources']['num_machines']:
                print("num_machines {} , calculation_set['resources']['num_machines'] {},".format(
                      num_machines, calculation_set['resources']['num_machines']  ))
                print("num_machines > calculation_set['resources']['num_machines']")
                c = c*2 

        if c_index and v_index:
            X_para[c_index] = c  
            X_para[v_index] = v
        X_string = " ".join([str(it) for it in X_para])
        if X_string.strip() == '':
            mpi_per = calculation_set['resources']['num_mpiprocs_per_machine'] 
            num_mach = calculation_set['resources']['num_machines']
            c = mpi_per if mpi_per > num_mach else num_mach
            v = mpi_per if mpi_per < num_mach else num_mach
            X_string = '1  1 {c} {v}'.format(c=c, v=v )
        calculation_set['resources']['num_machines'] = num_machines
        calculation_set['resources']['num_mpiprocs_per_machine'] = num_mpiprocs_per_machine
        return X_string , calculation_set
            
    if typ == 'SE_CPU':
        #SE_ROLEs = "q qp b"
        #SE_CPU = "1 32 96"
        SE_para  = [ int(it) for it in values.strip().split(' ') if it ]
        try:
            qp_index = roles.split(' ').index("qp")
            b_index = roles.split(' ').index("b")
            qp = SE_para[qp_index] or  1
            b  = SE_para[b_index] or 1  
        except ValueError:
            qp_index = b_index = 0
            qp =1
            b  =1  
        except IndexError:
            qp_index = b_index = 0
            qp =1
            b  =1  
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
        if SE_string.strip() == '':
            mpi_per = calculation_set['resources']['num_mpiprocs_per_machine']
            num_mach = calculation_set['resources']['num_machines']
            c = mpi_per if mpi_per > num_mach else num_mach
            v = mpi_per if mpi_per < num_mach else num_mach
            SE_string = '1   {v} {c}'.format(c=c, v=v )
        
        calculation_set['resources']['num_machines'] = num_machines
        calculation_set['resources']['num_mpiprocs_per_machine'] = num_mpiprocs_per_machine
        return SE_string, calculation_set
   

default_step_size = {
               'PPAPntXp': .2,   
               'NGsBlkXp': .1,   
               'BSENGBlk': .1,  
               'BSENGexx': .2,
               'BndsRnXp': .1, 
               'GbndRnge': .1,
               'BSEBands': 2, # 
               'FFTGvecs': .2,
                }

def update_parameter_field( field, starting_point, update_delta):
    # Bug 
    if field in ['PPAPntXp','NGsBlkXp','BSENGBlk','BSENGexx','FFTGvecs']: # single numbers
        new_field_value =  starting_point  + update_delta 
        return new_field_value
    elif field == 'BndsRnXp':
        new_hi_value =  int( starting_point  + update_delta )
        new_low_value =  int( starting_point  - update_delta )
        return (new_low_value , new_hi_value)
    elif field == 'GbndRnge':
        new_field_value =  int( starting_point   + update_delta )
        return (1, new_field_value)
    elif field == 'BSEBands':  # Will be useful when we support BSE calculations
        hi =  starting_point +   update_delta
        low  =  starting_point  -  update_delta
        return ( low, hi )
    else:
        raise WorkflowInputValidationError("convergences the field {} are not supported".format(field))


def set_default_qp_param(parameter=None):
    """
    """
    if not parameter:
       parameter = ParameterData(dict={})
    edit_param = parameter.get_dict()
    if 'ppa' not in edit_param.keys():
        edit_param['ppa'] = True
    if 'gw0' not in edit_param.keys():
        edit_param['gw0'] = True
    if 'HF_and_locXC' not in edit_param.keys():
        edit_param['HF_and_locXC'] = True
    if 'em1d' not in edit_param.keys():
        edit_param['em1d'] = True
    if 'DysSolver' not in edit_param.keys():
        edit_param['DysSolver'] = "n"
    if 'Chimod' not in edit_param.keys():
        edit_param['Chimod'] = "Hartree"
    if 'LongDrXp' not in edit_param.keys():
        edit_param['LongDrXp'] = (1.000000,0.000000, 0.000000)
    if 'PPAPntXp' not in edit_param.keys():
        edit_param['PPAPntXp'] =  4
        edit_param['PPAPntXp_units'] =  'eV'
    if 'SE_CPU' not in  edit_param.keys():
        edit_param['SE_CPU'] ="1 8 16" 
        edit_param['SE_ROLEs']= "q qp b"
    if 'X_all_q_CPU' not in  edit_param.keys():
        edit_param['X_all_q_CPU']= "1 1 16 8"
        edit_param['X_all_q_ROLEs'] ="q k c v"
    if 'FFTGvecs' not in edit_param.keys():
        edit_param['FFTGvecs'] =  8
        edit_param['FFTGvecs_units'] =  'Ry'
    return ParameterData(dict=edit_param)



def set_default_pw_param(nscf=False):
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
              'ecutwfc': 25.,
              'occupations':'smearing',
              'degauss': 0.001,
              'starting_magnetization(1)' : 0.0,
              'smearing': 'fermi-dirac',
              },
          'ELECTRONS': {
              'conv_thr': 1.e-8,
              'electron_maxstep ': 100,
              'mixing_mode': 'plain',
              'mixing_beta' : 0.3,
              } }
    if nscf:
        pw_parameters['CONTROL']['calculation'] = 'nscf'
        pw_parameters['SYSTEM']['force_symmorphic'] =  True 
    return ParameterData(dict=pw_parameters)

def default_pw_settings():
    return ParameterData(dict={})
 
def yambo_default_settings():
    return ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                             'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'] })      
 
def p2y_default_settings():
    return ParameterData(dict={ "ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','l-*','l_*','LOG/l-*_CPU_1'], 'INITIALISE':True})


def default_qpkrange(calc_pk, parameters):
    calc = load_node(calc_pk)
    edit_parameters = parameters.get_dict()
    if isinstance(calc,PwCalculation):
       nelec = calc.out.output_parameters.get_dict()['number_of_electrons']
       nocc = None
       if calc.out.output_parameters.get_dict()['lsda']== True or\
          calc.out.output_parameters.get_dict()['non_colinear_calculation'] == True:
          nocc = nelec/2 
       else:
          nocc = nelec/2
       is_pw = True
       nkpts = calc.out.output_parameters.get_dict()['number_of_k_points']
       if 'QPkrange' not in edit_parameters.keys():
            edit_parameters['QPkrange'] = [(1,1 , int(nocc) , int(nocc)+1 )]
    return ParameterData(dict=edit_parameters)

def split_incom(num):
    powers = []
    i = 1
    while i <= num:
        if i & num:
            powers.append(i)
        i <<= 1
    larges_p = powers[-1]
    power = int(math.log(larges_p)/math.log(2))
    if power%2 == 0:
        return (2**(power*3/4), 2**(power*1/4))
    else:
        return (2**(power*2/3), 2**(power*1/3))

def is_converged(values,conv_tol=1e-5,conv_window=3):
    """Check convergence for a list of values
    
    If the change between successive iterations is less than conv_tol for conv_window iterations
    the list is said to be converged.

    :param values: list of values in input
    :param conv_tol: convergence tolerance (optional, default = 1e-5)
    :param conv_window: number of last iterations considered (optional, default = 3)
    :rtype: Bool
    """
    delta_list = []
    for i in range(1,len(values)):
        delta_list.append(abs(values[i]-values[i-1]))
    delta_list = delta_list[-conv_window:]
    return any(x<conv_tol for x in delta_list) 
