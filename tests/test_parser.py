from __future__ import absolute_import
import unittest
from aiida.manage.fixtures import PluginTestCase


class TestHartreeLog(PluginTestCase):
    def setUp(self):
        """
        """
        example_out = {"errors": [], "warnings": [], "yambo_wrote": False}
        from aiida.plugins.utils import DataFactory
        from aiida.orm.nodes.parameter import Dict
        self.exampleparam = Dict(dict=example_out)
        self.exampleparam.store()

    def tearDown(self):
        """
        """
        pass

    def test_simple_log(self):
        from aiida.orm import load_node
        assert load_node(self.exampleparam.pk)
