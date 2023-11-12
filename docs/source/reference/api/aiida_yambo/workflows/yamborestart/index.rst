:py:mod:`aiida_yambo.workflows.yamborestart`
============================================

.. py:module:: aiida_yambo.workflows.yamborestart


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yamborestart.YamboRestart




.. py:class:: YamboRestart(*args, **kwargs)


   Bases: :py:obj:`aiida_quantumespresso.workflows.protocols.utils.ProtocolMixin`, :py:obj:`aiida.engine.processes.workchains.restart.BaseRestartWorkChain`

   This module interacts directly with the yambo plugin to submit calculations

   This module submits calculations using the yambo plugin, and manages them, including
   restarting the calculation in case of:
   1. Memory problems (will reduce MPI parallelism before resubmitting) -- to be fixed
   2. Queue time exhaustions (will increase time by a fraction before resubmitting)
   3. Parallelism errors (will reduce the MPI the parallelism before resubmitting)  -- to be fixed
   4. Errors originating from a few select unphysical input parameters like too low bands.  -- to be fixed

   .. py:attribute:: _process_class

      

   .. py:attribute:: _error_handler_entry_point
      :value: 'aiida_yambo.workflow_error_handlers.yamborestart'

      

   .. py:method:: define(spec)
      :classmethod:

      Define the process specification.


   .. py:method:: get_protocol_filepath()
      :classmethod:

      Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols.


   .. py:method:: get_builder_from_protocol(preprocessing_code, code, protocol='fast', overrides={}, parent_folder=None, NLCC=False, RIM_v=False, RIM_W=False, **_)
      :classmethod:

      Return a builder prepopulated with inputs selected according to the chosen protocol.
      :return: a process builder instance with all inputs defined ready for launch.


   .. py:method:: setup()

      setup of the calculation and run
              


   .. py:method:: validate_parameters()

      validation of the input parameters... including settings and the namelist...
      for example, the parallelism namelist is different from version the version... 
      we need some input helpers to fix automatically this with respect to the version of yambo


   .. py:method:: validate_resources()

      validation of machines... completeness and with respect para options
              


   .. py:method:: validate_parent()

      validation of the parent calculation --> should be at least nscf/p2y
              


   .. py:method:: report_error_handled(calculation, action)

      Report an action taken for a calculation that has failed.
      This should be called in a registered error handler if its condition is met and an action was taken.
      :param calculation: the failed calculation node
      :param action: a string message with the action taken


   .. py:method:: _handle_unrecoverable_failure(calculation)

      Handle calculations with an exit status below 400 which are unrecoverable, 
      so abort the work chain.


   .. py:method:: _handle_unknown_error(calculation)

      Handle calculations for an unknown reason; 
      we copy the SAVE already created, if any.


   .. py:method:: _handle_walltime_error(calculation)

      Handle calculations for a walltime error; 
      we increase the simulation time and copy the database already created.


   .. py:method:: _handle_parallelism_error(calculation)

      Handle calculations for a parallelism error; 
      we try to change the parallelism options.


   .. py:method:: _handle_memory_error(calculation)

      Handle calculations for a memory error; 
      we try to change the parallelism options, in particular the mpi-openmp balance.
      if cpu_per_task(mpi/node) is already set to 1, we can increase the number of nodes,
      accordingly to the inputs permissions.


   .. py:method:: _handle_variable_NOT_DEFINED(calculation)

      Handle calculations Variable NOT DEFINED error, happens with ndb.pp_fragments.
      redo the calculation, trying to delete the wrong fragment and recompute it.



