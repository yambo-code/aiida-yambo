:py:mod:`aiida_yambo.workflows.utils.helpers_aiida_yambo`
=========================================================

.. py:module:: aiida_yambo.workflows.utils.helpers_aiida_yambo

.. autoapi-nested-parse::

   Classes for calcs e wfls analysis.



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_aiida_yambo.set_parallelism
   aiida_yambo.workflows.utils.helpers_aiida_yambo.calc_manager_aiida_yambo
   aiida_yambo.workflows.utils.helpers_aiida_yambo.updater
   aiida_yambo.workflows.utils.helpers_aiida_yambo.take_quantities
   aiida_yambo.workflows.utils.helpers_aiida_yambo.start_from_converged



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_aiida_yambo._has_netcdf


.. py:data:: _has_netcdf
   :value: False

   

.. py:function:: set_parallelism(instructions_, inputs, k_quantity)


.. py:function:: calc_manager_aiida_yambo(calc_info={}, wfl_settings={})


.. py:function:: updater(calc_dict, inp_to_update, parameters, workflow_dict, internal_iteration, ratio=False)


.. py:function:: take_quantities(calc_dict, workflow_dict, steps=1, what=['gap_eV'], backtrace=1)


.. py:function:: start_from_converged(inputs, node_uuid, mesh=False)


