:py:mod:`aiida_yambo.workflows.yambowf`
=======================================

.. py:module:: aiida_yambo.workflows.yambowf


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yambowf.YamboWorkflow



Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yambowf.clean
   aiida_yambo.workflows.yambowf.sanity_check_QP
   aiida_yambo.workflows.yambowf.merge_QP
   aiida_yambo.workflows.yambowf.extend_QP
   aiida_yambo.workflows.yambowf.QP_mapper
   aiida_yambo.workflows.yambowf.QP_subset_groups
   aiida_yambo.workflows.yambowf.QP_list_merger



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.yambowf.LegacyUpfData
   aiida_yambo.workflows.yambowf.SingleFileData


.. py:data:: LegacyUpfData

   

.. py:data:: SingleFileData

   

.. py:function:: clean(node)


.. py:function:: sanity_check_QP(v, c, input_db, output_db, create=True)


.. py:function:: merge_QP(filenames_List, output_name, ywfl_pk, qp_settings)


.. py:function:: extend_QP(filenames_List, output_name, ywfl_pk, qp_settings, QP)


.. py:function:: QP_mapper(ywfl, tol=1, full_bands=False, spectrum_tol=1)


.. py:function:: QP_subset_groups(nnk_i, nnk_f, bb_i, bb_f, qp_per_subset)


.. py:function:: QP_list_merger(l=[], qp_per_subset=10, consider_only=[-1])


.. py:class:: YamboWorkflow(inputs: dict | None = None, logger: logging.Logger | None = None, runner: aiida.engine.runners.Runner | None = None, enable_persistence: bool = True)


   Bases: :py:obj:`aiida_quantumespresso.workflows.protocols.utils.ProtocolMixin`, :py:obj:`aiida.engine.WorkChain`

   This workflow will perform yambo calculation on the top of scf+nscf or from scratch,
   using also the PwBaseWorkChain.

   .. py:attribute:: pw_exclude
      :value: ['parent_folder', 'pw.parameters', 'pw.pseudos', 'pw.code', 'pw.structure', 'kpoints']

      

   .. py:method:: define(spec)
      :classmethod:

      Workfunction definition

              


   .. py:method:: get_protocol_filepath()
      :classmethod:

      Return ``pathlib.Path`` to the ``.yaml`` file that defines the protocols.


   .. py:method:: get_builder_from_protocol(pw_code, preprocessing_code, code, protocol_qe='moderate', protocol='moderate', calc_type='gw', structure=None, overrides={}, parent_folder=None, NLCC=False, RIM_v=False, RIM_W=False, electronic_type=ElectronicType.METAL, spin_type=SpinType.NONE, initial_magnetic_moments=None, pseudo_family=None, **_)
      :classmethod:

      Return a builder prepopulated with inputs selected according to the chosen protocol.
      :return: a process builder instance with all inputs defined ready for launch.


   .. py:method:: validate_parameters()


   .. py:method:: start_workflow()

      Initialize the workflow, set the parent calculation

      This function sets the parent, and its type
      there is no submission done here, only setting up the neccessary inputs the workchain needs in the next
      steps to decide what are the subsequent steps


   .. py:method:: can_continue()

      This function checks the status of the last calculation and determines what happens next, including a successful exit


   .. py:method:: perform_next()

      This function  will submit the next step, depending on the information provided in the context

      The next step will be a yambo calculation if the provided inputs are a previous yambo/p2y run
      Will be a PW scf/nscf if the inputs do not provide the NSCF or previous yambo parent calculations


   .. py:method:: post_processing_needed()


   .. py:method:: run_post_process()


   .. py:method:: should_run_bse()


   .. py:method:: prepare_and_run_bse()


   .. py:method:: report_wf()



