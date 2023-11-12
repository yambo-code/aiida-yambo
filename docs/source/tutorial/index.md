(tutorials)=

# Tutorials

We show below a few examples on how to run Yambo calculations using AiiDA.

:::{important}
These tutorials assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. 
You can check the main [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html), 
[aiida-quantumespresso documentation](https://aiida-quantumespresso.readthedocs.io/en/latest/)
and [yambo-code documentation](https://www.yambo-code.eu) for more information on how to perform these steps.
:::

## Jupyter-based tutorials

We prepared an interactive, progressive and self-explained version of the tutorial, based on jupyter 
notebooks. The studied system will be the bulk Silicon, as you can see in the examples/examples_Silicon folder. We will make use of the protocol automatic 
inputs generation, still an experimental features for MBPT simulations within Yambo.

1. [Ground state properties](): get started with predicting the phonon dispersion of silicon.
2. [A first G0W0 calculation](): compute the dielectric and Raman tensors of silicon.
3. [Raman spectra](): learn the automated calculation of Raman spectra of silicon.
4. [Polar materials](): predict the phonon and dielectric properties of AlAs with LO-TO splitting.
5. [Spectra using different functionals](): compute the vibrational spectra of LiCo{sub}`2` using DFT and __DFT+U+V__, and understand the power of Hubbard corrections comparing the results to experiments!


Within the package you can also find example scripts to run each workchain for the hBN case;
these can be found in the examples/examples_hBN folder.


