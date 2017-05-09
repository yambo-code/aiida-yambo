import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

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
    inputs.kpoints=kpoints
    inputs.parameters = parameters  
    inputs.pseudo = get_pseudo(structure, str(pseudo_family))
    inputs.settings  = settings
    #if gamma:
    #    inputs.settings = ParameterData(dict={'gamma_only':True})
    return  inputs


