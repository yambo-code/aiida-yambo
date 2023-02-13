.. _sec.yambo_start:

Get started
---------------------------------

Overview
^^^^^^^^
`AiiDA Yambo`_ is a package that allows to automate many-body perturbation theory calculations using the Yambo code in the AiiDA framework.
Currently, the aiida-yambo plugin supports 
quasiparticle (G0W0 and COSHEX level) 
and optical properties (IP-RPA and BSE) simulations, 
as well as interfaces with different codes (e.g., Quantum ESPRESSO and Wannier90). 

We show below a few examples on how to submit Yambo calculations using AiiDA.

Note: these tutorials assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. You can check the main `AiiDA-core documentation`_ and `Yambo documentation`_ for more information on how to perform these steps.

.. _AiiDA Yambo: https://github.com/yambo-code/yambo-aiida
.. _available online: https://github.com/yambo-code/yambo-aiida/releases
.. _AiiDA Yambo Documentation: http://aiida-yambo.readthedocs.org
.. _AiiDA-core documentation : http://aiida-core.readthedocs.io/en/latest/index.html
.. _Yambo documentation : http://www.yambo-code.org/

Installation
^^^^^^^^^^^^

.. toctree::
   :maxdepth: 4

   installation

A script-based tutorial and a jupyter-based tutorial
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the following, we will show how to run calculations for bulk hBN using scripts, i.e. from the command line; 
these can be found in the examples/examples_hBN folder.
However, we prepared also an interactive and self-explained version of tutorials, based on jupyter notebooks and the bulk Silicon, 
in the examples/examples_Silicon folder. (In the latter version, we will make use of the protocol automatic 
inputs generation, still an experimental features for MBPT simulations within Yambo.)


First steps: ground state properties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   dft_p2y
   
A first G0W0 calculation
^^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   tutorial_gw

Plugin utilities & tips
^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   features

