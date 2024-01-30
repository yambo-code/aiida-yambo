:py:mod:`aiida_yambo.workflows.utils.helpers_yamborestart`
==========================================================

.. py:module:: aiida_yambo.workflows.utils.helpers_yamborestart

.. autoapi-nested-parse::

   Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.helpers_yamborestart.fix_parallelism
   aiida_yambo.workflows.utils.helpers_yamborestart.fix_memory
   aiida_yambo.workflows.utils.helpers_yamborestart.fix_time



.. py:function:: fix_parallelism(resources, failed_calc)

   bands, qp, last_qp, runlevels = find_gw_info(failed_calc.inputs)
   nscf = find_pw_parent(failed_calc,calc_type=['nscf']) 
   occupied = gap_mapping_from_nscf(nscf.pk,)['valence']
   mesh = nscf.inputs.kpoints.get_kpoints_mesh()[0]
   kpoints = gap_mapping_from_nscf(nscf.pk,)['number_of_kpoints']

   if 'gw0' or 'HF_and_locXC' in runlevels:
       new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine'],                                                         resources['num_cores_per_mpiproc'], bands,                                                         occupied, qp, kpoints,                                                        last_qp, namelist = {})
   elif 'bse' in runlevels:
       pass


.. py:function:: fix_memory(resources, failed_calc, exit_status, max_nodes, iteration)


.. py:function:: fix_time(options, restart, max_walltime)


