.. _tut-ref-to-yambo-tutorial:

Yambo Workflows Tutorial
========================

.. toctree::
   :maxdepth: 2

The following shows how to use the workflows provided by the  `aiida yambo` plugin.


YamboRestartWf
--------------

This is the basic workflow and will run a single yambo calculation, with a tolerance
for failed calculations, and it will restart calculations that have failed due to

- Time Exhaustion on the queue.
- Memory errors.

After each calculation, this workflow will check the exit status(provided by the parser) and, if the calculation is failed,
try to fix some parameters in order to resubmit the calculation and obtain results. As inputs, we have to provide
the maximum number of attempted restarts.

Example usage:

.. include:: ../../../../examples/test_wf/yambo_restart.py
   :literal:


YamboWorkflow
--------------

The `YamboWorkflow`  provides the functionality to run GW calculation from the PW step, passing in all the required
parameters for both the  KS DFT step with PW and the subsequent GW step. It uses the PwBaseWorkchain from `aiida-quantumespresso`
as a subworkflow to perform the first  DFT part and the `YamboRestartWf`  for the GW part.

Example usage.

.. include:: ../../../../examples/test_wf/yambo_wfl.py
   :literal:


YamboConvergence
----------------------------

The `YamboConvergence` provides the functionality to run G0W0 calculations(using YamboWorkflow) over several parameters,
and it can be used (for now) to perform multi-parameter investigation of the quasiparticle corrections.
It is possible to accomplish automatic convergence by iteration over one or more parameter in a serial way,
or to explore a provided 2-dimensional space of parameters, in order to perform a successive extrapolation of the results.
Let's see the case of automatic convergence over an arbitrary number of parameters ("type": 1D_convergence):

Example usage:

.. include:: ../../../../examples/test_wf/yambo_convergence.py
   :literal:

As you can see, we have to provide workflow_settings, which encode some workflow logic:

::

    {'type':'1D_convergence','what':'gap','where':[(k_v,vbM,k_c,cbm)],'where_in_words':['Gamma']})

The workflow submitted here looks for convergence on different parameters, searching each step a given parameter(1D). The quantity that tries
to converge is the gap('what') between given bands evaluated at fixed k-points. It is possible to choose also and indirect gap(notice that,
changing the k-point mesh, the k-points will change index). The other functionality of the converge workflow is to converge single levels
('gap'->'single-levels', [(k_v,vbM,k_c,cbm)]->[(k,b)]), useful in the study of molecules. It is possible also to search convergence simultaneously for
multiple gaps/levels, just adding tuples in the 'where' list. The workflow will take care of it and doesn't stop until all the quantities are
converged(or the maximum restarts are reached).

The complete workflow will return the results of the convergence iterations, as well as a final converged calculation, from which we can parse the
converged parameters, and a complete story of all the calculations of the workflow with all the information provided.

The data can be plotted using a function in :

::

    from aiida_yambo.utils.plot_utilities import plot_conv
    plot_conv(<workflow_pk>,title='Gap at Gamma for bulk hBN')


.. image:: ../../images/conv_hBN.png


Let's see the case of 2-dimensional space exploration:

Example usage:

.. include:: ../../../../examples/test_wf/yambo_2d_space.py
   :literal:

It is possible to use some functions(that may be as a starting point for more complex parsing) to parse and plot the results of
this type of workflow, in order to perform successive analysis.

.. image:: ../../images/2d_hBN.png
