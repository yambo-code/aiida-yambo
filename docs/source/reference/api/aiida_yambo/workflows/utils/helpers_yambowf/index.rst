:py:mod:`aiida_yambo.workflows.utils.helpers_yambowf`
=====================================================

.. py:module:: aiida_yambo.workflows.utils.helpers_yambowf

.. autoapi-nested-parse::

   Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_yambowf.check_kpoints_in_qe_grid
   aiida_yambo.workflows.utils.helpers_yambowf.QP_bands
   aiida_yambo.workflows.utils.helpers_yambowf.QP_bands_interface
   aiida_yambo.workflows.utils.helpers_yambowf.quantumespresso_input_validator
   aiida_yambo.workflows.utils.helpers_yambowf.add_corrections
   aiida_yambo.workflows.utils.helpers_yambowf.parse_qp_level
   aiida_yambo.workflows.utils.helpers_yambowf.parse_qp_gap
   aiida_yambo.workflows.utils.helpers_yambowf.parse_excitons
   aiida_yambo.workflows.utils.helpers_yambowf.additional_parsed
   aiida_yambo.workflows.utils.helpers_yambowf.organize_output
   aiida_yambo.workflows.utils.helpers_yambowf.QP_analyzer



.. py:function:: check_kpoints_in_qe_grid(qe_grid, point)


.. py:function:: QP_bands(node, QP_merged=None, mapping=None, only_scissor=False, plot=False)


.. py:function:: QP_bands_interface(node, mapping, only_scissor=Bool(False))


.. py:function:: quantumespresso_input_validator(workchain_inputs, overrides={'pw': {}})


.. py:function:: add_corrections(workchain_inputs, additional_parsing_List)


.. py:function:: parse_qp_level(calc, level_map)


.. py:function:: parse_qp_gap(calc, gap_map)


.. py:function:: parse_excitons(calc, what)


.. py:function:: additional_parsed(calc, additional_parsing_List, mapping)


.. py:function:: organize_output(output, node=None)


.. py:function:: QP_analyzer(pk, QP_db, mapping)


