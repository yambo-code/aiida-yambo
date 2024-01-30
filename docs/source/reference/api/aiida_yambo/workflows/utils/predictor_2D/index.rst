:py:mod:`aiida_yambo.workflows.utils.predictor_2D`
==================================================

.. py:module:: aiida_yambo.workflows.utils.predictor_2D


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.predictor_2D.The_Predictor_2D



Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.workflows.utils.predictor_2D.create_grid



.. py:function:: create_grid(edges=[], delta=[], alpha=0.25, add=[[], []], var=['BndsRnXp', 'NGsBlkXp'], shift=[0, 0])


.. py:class:: The_Predictor_2D(**kwargs)


   Class to analyse the convergence behaviour of a system
   using the new algorithm.

   .. py:method:: plot_scatter_contour_2D(fig, ax, x, y, z, vmin, vmax, colormap='gist_rainbow_r', marker='s', lw=7, label='', just_points=False, bar=False)


   .. py:method:: fit_space_2D(fit=False, alpha=1, beta=1, reference=None, verbose=True, plot=False, dim=100, colormap='gist_rainbow_r', b=None, g=None, save=False, thr_fx=5e-05, thr_fy=5e-05, thr_fxy=1e-08)


   .. py:method:: determine_next_calculation(overconverged_values=[], plot=False, colormap='gist_rainbow_r', reference=None, save=False)


   .. py:method:: check_the_point(old_hints={})


   .. py:method:: analyse(old_hints={}, reference=None, plot=False, save_fit=False, save_next=False, colormap='viridis', thr_fx=5e-05, thr_fy=5e-05, thr_fxy=1e-08)



