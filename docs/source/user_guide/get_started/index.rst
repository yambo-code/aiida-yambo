.. _sec.yambo_start:

Get started
---------------------------------

Overview
^^^^^^^^
`AiiDA Yambo`_ is a package that allows to automate many-body perturbation theory calculations using the Yambo code in the AiiDA framework.
For now, it is possible to compute independent particle optical spectra and G0W0 quasiparticle corrections. This is the starting point to compute fully converged
quasiparticle band structures, quantities that are directly related with optical experiments such as direct and inverse photoemission. 
In the future it will be possible also to compute other quantities that are already available from the Yambo code (such as excitonic effects and real time spectroscopy).

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


First steps: DFT to Yambo initialization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   dft_p2y
   
Plugin tutorial: a G0W0 calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   tutorial_gw

Plugin utilities & tips
^^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
   :maxdepth: 4

   features


