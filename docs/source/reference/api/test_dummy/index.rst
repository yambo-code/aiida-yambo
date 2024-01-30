:py:mod:`test_dummy`
====================

.. py:module:: test_dummy


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   test_dummy.fixture_work_directory
   test_dummy.fixture_computer_localhost
   test_dummy.test_naive_parser



Attributes
~~~~~~~~~~

.. autoapisummary::

   test_dummy.pytest_plugins


.. py:data:: pytest_plugins
   :value: ['aiida.manage.tests.pytest_fixtures']

   

.. py:function:: fixture_work_directory()

   Return a temporary folder that can be used as for example a computer's work directory.


.. py:function:: fixture_computer_localhost(fixture_work_directory)

   Return a `Computer` instance mocking a localhost setup.


.. py:function:: test_naive_parser(fixture_computer_localhost)


