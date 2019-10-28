from __future__ import absolute_import
import sys
import unittest
from aiida.manage.fixtures import TestRunner

tests = unittest.defaultTestLoader.discover('./tests')
result = TestRunner().run(tests, backend='django')

# Note: On travis, this will not fail even if the tests fail.
# Uncomment the lines below, when aiida 0.12.2 is released to fix this.
exit_code = int(not result.wasSuccessful())
sys.exit(exit_code)
