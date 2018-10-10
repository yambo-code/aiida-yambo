import unittest
from aiida.utils.fixtures import PluginTestCase
import subprocess, os

def backend_obj_users():
    """Test if aiida accesses users through backend object."""
    backend_obj_flag = False
    try:
        from aiida.backends.utils import get_automatic_user  # pylint: disable=unused-variable,no-name-in-module
    except ImportError:
        backend_obj_flag = True
    return backend_obj_flag

def get_current_user():
    """Get current user backwards compatibly with aiida-core <= 0.12.1."""
    current_user = None
    if backend_obj_users():
        from aiida.orm.backend import construct_backend  # pylint: disable=no-name-in-module
        backend = construct_backend()
        current_user = backend.users.get_automatic_user()
    else:
        from aiida.backends.utils import get_automatic_user  # pylint: disable=no-name-in-module
        current_user = get_automatic_user()
    return current_user

def create_authinfo(computer):
    """
    Allow the current user to use the given computer.
    Deal with backwards compatibility down to aiida 0.11
    """
    from aiida.backends.utils import load_dbenv, is_dbenv_loaded
    if not is_dbenv_loaded():
        load_dbenv()
    from aiida.orm import backend as orm_backend
    authinfo = None
    if hasattr(orm_backend, 'construct_backend'):
        backend = orm_backend.construct_backend()
        authinfo = backend.authinfos.create(computer=computer, user=get_current_user())
    else:
        from aiida.backends.djsite.db.models import DbAuthInfo
        authinfo = DbAuthInfo(dbcomputer=computer.dbcomputer, aiidauser=get_current_user())
    return authinfo


class TestWf (PluginTestCase):

    def setUp(self):
        """
        """
        from aiida import work
        from aiida.orm.code import Code
        from aiida.orm.data.parameter import ParameterData
        from aiida.orm.data.structure import StructureData
        from aiida.orm.data.remote import RemoteData
        from ase.spacegroup import crystal
        from aiida_quantumespresso.calculations.pw import PwCalculation
        from aiida_yambo.calculations.gw  import YamboCalculation
        from aiida.common.links import LinkType
        from aiida.orm.computer import Computer as AiidaOrmComputer
        from aiida.common.datastructures import calc_states
        from aiida.orm.utils import DataFactory
        runner = work.Runner(poll_interval=0., rmq_config=None, enable_persistence=None)
        work.set_runner(runner)
        self.computer = AiidaOrmComputer(name="testcase") 
        # conf_attrs hostname, description, enabled_state, transport_type, scheduler_type,  workdir
        # mpirun_command , default_mpiprocs_per_machine,
        self.computer._set_hostname_string("localhost") 
        self.computer._set_enabled_state_string('True') 
        self.computer._set_transport_type_string("local") 
        self.computer._set_scheduler_type_string("direct") 
        self.computer._set_workdir_string("/tmp/testcase/{username}/base") 
        self.computer.store()
        create_authinfo(computer=self.computer).store()
        self.code_yambo = Code()
        self.code_yambo.label="yambo"
        os_env = os.environ.copy()
        yambo_path = subprocess.check_output(['which', 'mock_yambo'], env=os_env).strip()
        self.code_yambo.set_remote_computer_exec((self.computer, yambo_path ))
        self.code_yambo.set_input_plugin_name ('yambo.yambo')

        self.code_p2y = Code()
        self.code_p2y.label="p2y"
        p2y_path = subprocess.check_output(['which', 'mock_p2y'], env=os_env).strip()
        self.code_p2y.set_remote_computer_exec ((self.computer, p2y_path))
        self.code_p2y.set_input_plugin_name ( 'yambo.yambo')
        self.code_yambo.store()  
        self.code_p2y.store()  

        self.calc_pw = PwCalculation() 
        self.calc_pw.set_computer ( self.computer)
        self.calc_pw.set_resources({"num_machines": 1,"num_mpiprocs_per_machine": 16,'default_mpiprocs_per_machine': 16})
        StructureData = DataFactory('structure')
        cell=[[   15.8753100000,    0.0000000000,    0.0000000000],
            [0.0000000000 , 15.8753100000 , 0.0000000000],
            [0.0000000000  , 0.0000000000  , 2.4696584760]]
        s = StructureData(cell=cell)
        self.calc_pw.use_structure(s) 
        print(self.calc_pw.store_all(), " pw calc")
        pw_remote_folder = RemoteData(computer=self.computer, remote_path="/tmp/testcase/work/calcPW") 
        print(pw_remote_folder.store(), "pw remote data" )
        self.calc_pw._set_state (calc_states.PARSING)
        pw_remote_folder.add_link_from(self.calc_pw, label='remote_folder', link_type=LinkType.CREATE)

        outputs = ParameterData(dict= { "lsda":False, "number_of_bands": 80, "number_of_electrons":8.0 , "number_of_k_points":147,
                                        "non_colinear_calculation": False})
        outputs.store()
        outputs.add_link_from(self.calc_pw ,label='output_parameters', link_type=LinkType.CREATE)



        self.calc = YamboCalculation()
        self.calc.set_computer ( self.computer)
        self.calc.use_code( self.code_p2y)
        p2y_settings = {u'ADDITIONAL_RETRIEVE_LIST': [u'r-*', u'o-*', u'l-*',  u'l_*',  u'LOG/l-*_CPU_1'], u'INITIALISE': True} 
        yambo_settings = {u'ADDITIONAL_RETRIEVE_LIST': [u'r-*', u'o-*', u'l-*',  u'l_*',  u'LOG/l-*_CPU_1'] }
        self.calc.use_settings( ParameterData(dict= p2y_settings) )
        self.calc.set_resources({"num_machines": 1,"num_mpiprocs_per_machine": 16,'default_mpiprocs_per_machine': 16})
        self.calc.use_parent_calculation(self.calc_pw)
        print (self.calc.store_all(), " yambo calc" )
        self.calc._set_state (calc_states.PARSING)
        a=5.388
        cell = crystal('Si', [(0,0,0)], spacegroup=227, cellpar=[a, a, a, 90, 90, 90],primitive_cell=True)
        self.struc= StructureData(ase=cell)
        self.struc.store()
        self.parameters = ParameterData(dict= {
                 "BndsRnXp": [
                   1.0, 48.0
                 ], 
                 "Chimod": "Hartree", 
                 "DysSolver": "n", 
                 "FFTGvecs": 25, 
                 "FFTGvecs_units": "Ry", 
                 "GbndRnge": [
                   1.0, 48.0
                 ], 
                 "HF_and_locXC": True, 
                 "LongDrXp": [
                   1.0, 0.0, 0.0
                 ], 
                 "NGsBlkXp": 2, 
                 "NGsBlkXp_units": "Ry", 
                 "QPkrange": [
                   [
                     1, 145,3, 5
                   ]
                 ], 
                 "SE_CPU": "1 2 4", 
                 "SE_ROLEs": "q qp b", 
                 "X_all_q_CPU": "1 1 4 2", 
                 "X_all_q_ROLEs": "q k c v", 
                 "em1d": True, 
                 "gw0": True, 
                 "ppa": True, 
                 "rim_cut": True
               })
        self.yambo_settings = ParameterData(dict= {
               "ADDITIONAL_RETRIEVE_LIST": [
                 "r-*",  "o-*", "l-*", "l_*", "LOG/l-*_CPU_1", "aiida/ndb.QP", "aiida/ndb.HF_and_locXC" ]})
        self.p2y_settings = ParameterData(dict= {"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','l_*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC'], 'INITIALISE':True})
        self.yambo_calc_set =ParameterData(dict= {'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 16}, 'max_wallclock_seconds':  60*29,
                  'max_memory_kb': 1*88*1000000 ,"queue_name":"s3parvc3", #'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "1" }  })
        self.p2y_calc_set = ParameterData(dict= {'resources':  {"num_machines": 1,"num_mpiprocs_per_machine": 2}, 'max_wallclock_seconds':  60*2,
                  'max_memory_kb': 1*10*1000000 , "queue_name":"s3parvc3", # 'custom_scheduler_commands': u"#PBS -A  Pra14_3622" ,
                  'environment_variables': {"OMP_NUM_THREADS": "2" }  })
        self.remote_folder = RemoteData(computer=self.computer, remote_path="/tmp/testcase/work/calcX") 
        self.remote_folder.store()
        self.remote_folder.add_link_from(self.calc, label='remote_folder', link_type=LinkType.CREATE)
        self.calc._set_state (calc_states.FINISHED)
        #self.calc.store_all()

    def tearDown(self):
        """
        """
        pass

    def test_simple_log (self):
        from aiida.work.launch import run
        from aiida.orm.data.base import Float, Str, NumericType,  List, Bool
        from aiida_yambo.workflows.yamborestart  import YamboRestartWf
        p2y_result =  run (YamboRestartWf,
                     precode= Str('p2y'),
                    yambocode=Str('yambo'),
                    parameters = self.parameters,
                    calculation_set= self.yambo_calc_set ,
                    parent_folder = self.remote_folder , settings = self.yambo_settings )
        assert 'retrieved' in p2y_result
