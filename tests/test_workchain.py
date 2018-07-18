import unittest
from aiida.utils.fixtures import PluginTestCase

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
        from aiida_yambo.workflows.yamborestart  import YamboRestartWf
        from aiida_quantumespresso.calculations.pw import PwCalculation
        from aiida_yambo.calculations.gw  import YamboCalculation
        runner = work.Runner(poll_interval=0., rmq_config=None, enable_persistence=None)
        work.set_runner(runner)
        self.code_yambo = Code(name="yambocode")
        self.code_p2y = Code(name="yambocode")
        self.code_yambo.store()  
        self.code_p2y.store()  
        self.calc = YamboCalculation()
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
                 "HF_and_locXC": true, 
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
        self.remote_folder = RemoteData(computer=self.new_comp, remote_path="/tmp") 
        self.calc.store_all()
        self.remote_folder.add_link_from(self.calc, label='remote_folder', link_type=LinkType.CREATE)

    def tearDown(self):
        """
        """
        pass

    def test_simple_log (self):
        from aiida.work.launch import run
        from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData, Bool
        p2y_result =  run (YamboRestartWf,
                     precode= self.code_p2y,
                    yambocode=self.code_yambo,
                    parameters = self.parameters,
                    calculation_set= self.yambo_calc_set ,
                    parent_folder = parent_folder_, settings = self.yambo_settings )
        assert 'retrieved' in results
