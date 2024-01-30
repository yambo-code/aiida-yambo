:py:mod:`aiida_yambo.workflows.yamboconvergence`
================================================

.. py:module:: aiida_yambo.workflows.yamboconvergence


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yamboconvergence.YamboConvergence




Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yamboconvergence.YamboWorkflow


.. py:data:: YamboWorkflow

   

.. py:class:: YamboConvergence(inputs: dict | None = None, logger: logging.Logger | None = None, runner: aiida.engine.runners.Runner | None = None, enable_persistence: bool = True)


   Bases: :py:obj:`aiida_quantumespresso.workflows.protocols.utils.ProtocolMixin`, :py:obj:`aiida.engine.WorkChain`

   This workflow will perform yambo convergences with respect to some parameter. It can be used also to run multi-parameter
   calculations.

   .. py:method:: define(spec)
      :classmethod:

      Workfunction definition

              


   .. py:method:: get_protocol_filepath()
      :classmethod:

      Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols.


   .. py:method:: get_builder_from_protocol(pw_code, preprocessing_code, code, protocol_qe='moderate', protocol='moderate', calc_type='gw', structure=None, overrides={}, NLCC=False, RIM_v=False, RIM_W=False, parent_folder=None, electronic_type=ElectronicType.INSULATOR, spin_type=SpinType.NONE, initial_magnetic_moments=None, pseudo_family=None, **_)
      :classmethod:

      Return a builder prepopulated with inputs selected according to the chosen protocol.
      :return: a process builder instance with all inputs defined ready for launch.


   .. py:method:: start_workflow()

      Initialize the workflow


   .. py:method:: has_to_continue()

      This function checks the status of the last calculation and determines what happens next, including a successful exit


   .. py:method:: next_step()

      This function will submit the next step


   .. py:method:: data_analysis()


   .. py:method:: report_wf()


   .. py:method:: pre_needed()


   .. py:method:: do_pre()


   .. py:method:: prepare_calculations()



