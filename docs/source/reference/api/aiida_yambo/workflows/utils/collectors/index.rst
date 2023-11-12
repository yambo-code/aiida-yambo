:py:mod:`aiida_yambo.workflows.utils.collectors`
================================================

.. py:module:: aiida_yambo.workflows.utils.collectors


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.collectors.take_fermi
   aiida_yambo.workflows.utils.collectors.collect_all_params
   aiida_yambo.workflows.utils.collectors.collect_2D_results
   aiida_yambo.workflows.utils.collectors.parse_2D_data
   aiida_yambo.workflows.utils.collectors.get_timings



.. py:function:: take_fermi(calc_node_pk)


.. py:function:: collect_all_params(story, param_list=['BndsRnXp', 'GbndRnge', 'NGsBlkXp'])


.. py:function:: collect_2D_results(story=None, last_c=None, ef=0)


.. py:function:: parse_2D_data(wfl_pk, folder_name='', title='run', last_c_ok_pk=None)


.. py:function:: get_timings(story)


