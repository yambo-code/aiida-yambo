:py:mod:`aiida_yambo.workflows.utils.helpers_aiida_qe`
======================================================

.. py:module:: aiida_yambo.workflows.utils.helpers_aiida_qe

.. autoapi-nested-parse::

   Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully



Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_aiida_qe.calc_manager_aiida_qe




.. py:class:: calc_manager_aiida_qe(calc_info={})


   .. py:method:: updater(inp_to_update, k_distance, first)


   .. py:method:: take_quantities(start=1)


   .. py:method:: get_caller(calc, depth=2)


   .. py:method:: get_called(calc, depth=2)


   .. py:method:: start_from_converged(node, params)


   .. py:method:: set_relaxed_structure(last_ok)


   .. py:method:: set_parent(last_ok)


   .. py:method:: take_down(node=0, what='CalcJobNode')


   .. py:method:: take_super(node=0, what='WorkChainNode')



