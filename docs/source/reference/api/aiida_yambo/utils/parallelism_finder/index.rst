:py:mod:`aiida_yambo.utils.parallelism_finder`
==============================================

.. py:module:: aiida_yambo.utils.parallelism_finder


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.parallelism_finder.reorganize_resources
   aiida_yambo.utils.parallelism_finder.find_commensurate
   aiida_yambo.utils.parallelism_finder.balance
   aiida_yambo.utils.parallelism_finder.distribute
   aiida_yambo.utils.parallelism_finder.find_parallelism_qp



.. py:function:: reorganize_resources(mpi_new, nodes, mpi_per_node, threads)


.. py:function:: find_commensurate(a, b)


.. py:function:: balance(tasks, a, b, rec=0)


.. py:function:: distribute(tasks=10, what='DIP', **ROLEs)


.. py:function:: find_parallelism_qp(nodes, mpi_per_node, threads, bands, occupied=2, qp_corrected=2, kpoints=1, last_qp=2, namelist={})


