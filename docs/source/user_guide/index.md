(user-guide)=

# User guide & tutorials

In this section we presents several examples on how to run Calcjobs and WorkChains, as well as their description. 
We start from DFT and we go through GW and BSE steps.
For the sake of consistency, we consider the same system as the tutorials, i.e. the bulk hexagonal
Boron Nitride (hBN).

:::{important}
These how-to guides assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. 
You can check the main [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html), 
[aiida-quantumespresso documentation](https://aiida-quantumespresso.readthedocs.io/en/latest/)
and [yambo-code documentation](https://www.yambo-code.eu) for more information on how to perform these steps.
For tutorials on how to run AiiDA plugins, please have a look [here](https://aiida-tutorials.readthedocs.io/en/latest/index.html).
:::


```{toctree}
:maxdepth: 2

get_started/dft_p2y
get_started/tutorial_gw
workflows/index
```

## Interactive tutorial

We prepared an interactive, progressive and self-explained version of the tutorials, based on jupyter 
notebooks.
The studied system will be the bulk hBN, as you can see in the examples/examples_hBN folder. We will make use of the automatic protocol inputs generation, still an experimental features for MBPT simulations within Yambo.

:::{important}
These tutorials assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. 
You can check the main [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html), 
[aiida-quantumespresso documentation](https://aiida-quantumespresso.readthedocs.io/en/latest/)
and [yambo-code documentation](https://www.yambo-code.eu) for more information on how to perform these steps.

Moreover, these tutorials are provided in a separate github repository with respect to the aiida-yambo plugin. 
You should clone the [tutorials-aiida-yambo](https://github.com/mikibonacci/tutorials-aiida-yambo) repository, to have access to the notebook.
:::

0. [Some AiiDA prerequisites](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/01_structure_and_pseudos.ipynb): set up a crystal structure and pseudopotential family, crucial to run DFT+MBPT simulations.
1. [Ground state properties](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/02_QE_starting_point.ipynb): get started with computing self- and non self-consistent DFT steps.
2. [A first G0W0 calculation](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/2_YamboRestart_G0W0.ipynb): submit you first GW simulation.
3. [Enabling error handling](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/): learn the automated calculation of Raman spectra of silicon.
4. [-](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/): .
5. [-](https://github.com/mikibonacci/tutorials-aiida-yambo/blob/main/tutorial_hBN/):s!

Within the package you can also find example scripts to run each workchain for the hBN case;
these can be found in the examples/examples_hBN folder.