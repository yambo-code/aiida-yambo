:py:mod:`old_wc`
================

.. py:module:: old_wc


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   old_wc.TestWf



Functions
~~~~~~~~~

.. autoapisummary::

   old_wc.backend_obj_users
   old_wc.get_current_user
   old_wc.create_authinfo



.. py:function:: backend_obj_users()

   Test if aiida accesses users through backend object.


.. py:function:: get_current_user()

   Get current user backwards compatibly with aiida-core <= 0.12.1.


.. py:function:: create_authinfo(computer)

   Allow the current user to use the given computer.
   Deal with backwards compatibility down to aiida 0.11


.. py:class:: TestWf


   Bases: :py:obj:`aiida.manage.fixtures.PluginTestCase`

   .. py:method:: setUp()

              


   .. py:method:: tearDown()

              


   .. py:method:: test_simple_log()



