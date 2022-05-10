.. _p2y:

.. _my-ref-to-yambo-tutorial:

First steps into MBPT calculations
==================================

.. toctree::
   :maxdepth: 2

The following tutorial shows how to run all the necessary steps to obtain a the databases needed to start a Yambo calculation.
The starting point is a self-consistent calculation of the electronic density, and then a calculation of the electronic wavefunctions through
a non-self-consistent DFT calculation. So, the first AiiDA plugin used here is the QuantumEspresso one. 
Then, it is necessary to convert the results in Yambo-readable format, i.e. NetCDF format: this is done using the p2y executable, included in the
yambo package and executed from the same yambo plugin. 
In order to keep the tutorial light in terms of computational resources and time of execution, calculations are
not fully converged with respect to parameters such as k-points, empty bands or G-vectors.
The example here considers the bulk hexagonal boron nitride hBN. 

SCF step (Quantum ESPRESSO)
----------------------------

Using the AiiDA quantumespresso.pw plugin, we begin with submitting an SCF calculation.
We are going to use the ``pk`` of the SCF calculation in the next steps. Remember that the ``pk`` is the number that identifies the node in the AiiDA database. 
We use the PwBaseWorkChain to submit a pw calculation, in such  a way to have automatic
error handling and restarting from failed runs. 

For details on how to use the quantumespresso.pw plugin, please refer to the respective documentation page. Remember to replace the codename
and pseudo-family with those configured in your AiiDA installation. NB: Yambo can be used only with norm-conserving pseudopotentials!


.. include:: ../../../../examples/plugin/scf_baseWorkchain.py
   :literal:

As you can notice, we use the "argparse" module to provide some inputs from the shell, like the code and the pseudos to be used in
the simulation. In practice, the command to be run would be like:

::

    verdi run name_of_the_script.py --code <pk of the pw code> --pseudo <name of the pseudofamily>

this is just our choice to build the calculation, it is possible also to do it interactively (jupyter notebooks) or adapting the script to 
have no input to provide.

NSCF step (Quantum ESPRESSO) for G0W0
-------------------------------------
Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the GW calculation.

.. include:: ../../../../examples/plugin/nscf_baseWorkchain.py
   :literal:


P2Y step (Yambo)
-------------------------------------
Now we use the Yambo plugin to run the p2y code, converting the Quantum ESPRESSO files into a NetCDF Yambo database. The parent folder now
should be the nscf one.

.. include:: ../../../../examples/plugin/yambo_p2y.py
   :literal:

The fundamental input that tells the plugin to only run a p2y calculation is the settings key ``INITALISE``: if True, the SAVE folder is created and initialized using the p2y and yambo executables. 
An automatic procedure is implemented to decide what executables are needed to complete the calculation. 