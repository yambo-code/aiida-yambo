import unittest
from aiida.utils.fixtures import PluginTestCase

class TestHartreeLog (PluginTestCase):

    def setUp(self):
        """
        """
        example_out = {
                        "errors": [], 
                        "warnings": [], 
                        "yambo_wrote": False
                      }
        from aiida.orm.utils import DataFactory
        from aiida.orm.data.parameter import ParameterData
        self.exampleparam = ParameterData(dict= example_out)
        self.exampleparam.store() 

    def tearDown(self):
        """
        """
        pass

    def test_simple_log (self):
        from aiida.orm import load_node
        assert load_node(self.exampleparam.pk)
