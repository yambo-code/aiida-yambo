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
- tutorials-aiida-yambo/prerequisites: 
    - [AiiDA prerequisite](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/prerequisites/0_1_structure_and_pseudos.ipynb): how to set up structures, pseudopotentials and groups in AiiDA;
    - [aiida-quantumespresso prerequisite](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/prerequisites/0_2_QE_starting_point.ipynb): how to run the required DFT starting point, via the `aiida-quantumespresso` plugin;
- tutorials-aiida-yambo/yambo:
    - [Simple yambo calculation](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main//yambo/1_YamboCalculation_G0W0.ipynb);
    - [Enabling error handling](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/2_YamboRestart_G0W0.ipynb);
    - From scratch to yambo results: DFT+MBPT
        - [One G0W0 calculation](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/3_1_YamboWorkflow_G0W0.ipynb);
        - [Multiple QP calculations](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/3_2_YamboWorkflow_QP.ipynb);
        - [A BSE simulation using scissor&stretching corrections](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/5_1_YamboWorkflow_BSE.ipynb);
        - [A BSE simulation using explicit quasiparticle corrections](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/5_2_YamboWorkflow_BSE_QP.ipynb);
    - Automated convergence of MBPT:
        - [G0W0 case](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/4_YamboConvergence_G0W0.ipynb);
        - [BSE case](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/6_YamboConvergence_BSE.ipynb);
- tutorials-aiida-yambo/yambo_wannier90: interpolating band structures
    - [W90@QE](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/1_Band_interpolation_W90_DFT.ipynb);
    - [reference QE band structure](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/2_PwBands.ipynb);
    - [Fully automated W90@G0W0 interpolated band structure](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/3_Band_interpolation_W90_G0W0_full.ipynb)
    - [Analysis of W90@G0W0](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/hBN_analysis.ipynb).

Within the package you can also find example scripts to run each workchain for the hBN case;
these can be found in the examples/examples_hBN folder.