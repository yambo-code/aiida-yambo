:py:mod:`aiida_yambo.workflows.utils.extend_QPDB`
=================================================

.. py:module:: aiida_yambo.workflows.utils.extend_QPDB


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.extend_QPDB.build_ndbQP
   aiida_yambo.workflows.utils.extend_QPDB.FD_even
   aiida_yambo.workflows.utils.extend_QPDB.Apply_FD_scissored_correction
   aiida_yambo.workflows.utils.extend_QPDB.update_FD_and_scissor
   aiida_yambo.workflows.utils.extend_QPDB.FD_and_scissored_db



.. py:function:: build_ndbQP(db_path, DFT_pk, Nb=[1, 1], Nk=1, verbose=False)

   This just build a QP with KS results, then you can modify the script to change
   the values as you want. Or also just modify the output ds, which has already
   the right dimensions. 


.. py:function:: FD_even(x, mu, e_ref=0, T=1e-06)


.. py:function:: Apply_FD_scissored_correction(start, corrections, scissor, mu, e_ref=0, T=1e-06, unit=units.Ha)

   corrections should be a zeroes with shape of start, 
   filled only for the corrections that we computed explicitely.
   provide the scissors in Hartree units...


.. py:function:: update_FD_and_scissor(db_dft, db_gw, conduction, mu, scissors=[[1, 0], [1, 0]], e_ref=0, T=1e-06, verbose=False, full_bands=True)

   update with FD*realGW for the region of interest, then scissor(DFT) for the 
   outside region. 
   ds: the created ndb.QP
   db: the explicit GW corrections that we have.
   mu: window of energy needed in which we want the correction to be exact. except for the smearing of T>0. 


.. py:function:: FD_and_scissored_db(out_db_path, pw, Nb, Nk, v_max, c_min, fit_v, fit_c, conduction, e_ref=None, mu=None, T=0.01)


