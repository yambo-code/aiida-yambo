.. _tut-ref-to-yambo-conv2d:

YamboConvergence: fixed-path
----------------------------

The ``YamboConvergence`` workchain provides the functionalities to run multiple G0W0 calculations on the same system, over a wide range of chaging parameter. 
This represents the typical method to obtain an accurate evaluation of the quasiparticle correction: indeed, a lot of effort has to be done in order to find
the convergence with respect to parameters like empty states used to evaluate the Self Energy used to solve the quasiparticle equation.
There are cases in which convergences cannot be achieved exactly: this is, e.g., the case of molecules. In such a case, you may want to perform G0W0 
calculations on a give set of parameters/values and then, with an extrapolation, obtain the given result. 
This logic can be activated in the YamboConvergence, as we will see, and represents a new implementation that for now has not the extrapolation feature 
included. 

Let's see the case of fixed-path automation, activated by setting ``"type": 2D_space``:

.. include:: ../../../../examples/test_wf/yambo_2d_space.py
   :literal:

.. image:: ./images/hBN_3d_inv.png

The type is called '2D_space', but actually is possibile to change and arbitrary number of parameter at the time: the reason of the name is due to the fact that 
typically this investigation are done to observe the interdependence between bands and G-vectors cutoff. 
To see how to post process and plot results, we suggest to consult the dedicated section :ref:`conv_pp_2d`.