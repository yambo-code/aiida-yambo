:py:mod:`aiida_yambo.utils.gw2wannier90`
========================================

.. py:module:: aiida_yambo.utils.gw2wannier90


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.gw2wannier90.k_mapper
   aiida_yambo.utils.gw2wannier90.gw2wannier90



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.gw2wannier90.argv


.. py:data:: argv

   

.. py:function:: k_mapper(dense_mesh, coarse_mesh, VbM, Cbm)

   calcfunction to map k points of a coarse mesh in 
   a denser one. 
   the two inputs dense and coarse mesh are calc.outputs.output_band
   for each of the two calculations with the dense and coarse grid.
   then we have valence and conduction extrema, to be provided as Int()

   The output is then ready to update the key,val pair QPkrange,val in the
   yambo input parameters['variables'].


.. py:function:: gw2wannier90(seedname=Str('aiida'), options=List(['mmn', 'amn']), output_path=Str(''), nnkp_file=None, pw2wannier_parent=None)


