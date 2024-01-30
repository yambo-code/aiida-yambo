:py:mod:`aiida_yambo.workflows.utils.helpers_workflow`
======================================================

.. py:module:: aiida_yambo.workflows.utils.helpers_workflow

.. autoapi-nested-parse::

   Classes for calcs e wfls analysis.



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_workflow.conversion_wrapper
   aiida_yambo.workflows.utils.helpers_workflow.collect_inputs
   aiida_yambo.workflows.utils.helpers_workflow.create_space
   aiida_yambo.workflows.utils.helpers_workflow.update_space
   aiida_yambo.workflows.utils.helpers_workflow.convergence_workflow_manager
   aiida_yambo.workflows.utils.helpers_workflow.build_story_global
   aiida_yambo.workflows.utils.helpers_workflow.update_story_global
   aiida_yambo.workflows.utils.helpers_workflow.post_analysis_update
   aiida_yambo.workflows.utils.helpers_workflow.prepare_for_ce
   aiida_yambo.workflows.utils.helpers_workflow.analysis_and_decision
   aiida_yambo.workflows.utils.helpers_workflow.build_parallelism_instructions



.. py:function:: conversion_wrapper(func)


.. py:function:: collect_inputs(inputs, kpoints, ideal_iter)


.. py:function:: create_space(starting_inputs={}, workflow_dict={}, calc_dict={}, wfl_type='heavy', hint=None)


.. py:function:: update_space(starting_inputs={}, calc_dict={}, wfl_type='heavy', hint=0, existing_inputs={}, convergence_algorithm='smart')


.. py:function:: convergence_workflow_manager(parameters_space, wfl_settings, inputs, kpoints)


.. py:function:: build_story_global(calc_manager, quantities, workflow_dict={}, success=False)


.. py:function:: update_story_global(calc_manager, quantities, inputs, workflow_dict, success=False)


.. py:function:: post_analysis_update(inputs, calc_manager, oversteps, none_encountered, workflow_dict={}, success=False)


.. py:function:: prepare_for_ce(workflow_dict={}, keys=['gap_GG'], var_=[], var_full=[], bug_newton1d=False, new_algorithm=False)


.. py:function:: analysis_and_decision(calc_dict, workflow_manager, parameter_space=[], hints={})


.. py:function:: build_parallelism_instructions(instructions)


