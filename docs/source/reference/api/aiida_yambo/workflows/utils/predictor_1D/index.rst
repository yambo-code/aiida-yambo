:py:mod:`aiida_yambo.workflows.utils.predictor_1D`
==================================================

.. py:module:: aiida_yambo.workflows.utils.predictor_1D


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.predictor_1D.The_Predictor_1D



Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.predictor_1D.create_grid_1D



.. py:function:: create_grid_1D(edges=[], delta=[], alpha=1 / 3, add=[], var=['BndsRnXp'], shift=0)


.. py:class:: The_Predictor_1D(**kwargs)


   Class to analyse the convergence behaviour of a system
   using the new algorithm.

   .. py:method:: fit_space_1D(fit=False, alpha=1, beta=1, reference=None, verbose=True, plot=False, dim=100, b=None, g=None, save=False, thr_fx=5e-05)


   .. py:method:: determine_next_calculation(overconverged_values=[], plot=False, reference=None, save=False)


   .. py:method:: check_the_point(old_hints={})


   .. py:method:: analyse(old_hints={}, reference=None, plot=False, save_fit=False, save_next=False, colormap='viridis', thr_fx=5e-05)



