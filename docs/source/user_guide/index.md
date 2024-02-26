(user-guide)=

# User guide & tutorials

In this section we presents several examples on how to run Calcjobs and WorkChains, as well as their description. 
We start from DFT and we go through GW and BSE steps.

:::{important}
These how-to guides assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. 
You can check the main [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html), 
[aiida-quantumespresso documentation](https://aiida-quantumespresso.readthedocs.io/en/latest/)
and [yambo-code documentation](https://www.yambo-code.eu) for more information on how to perform these steps.
For tutorials on how to run AiiDA plugins, please have a look [here](https://aiida-tutorials.readthedocs.io/en/latest/index.html).

The following tutorials are provided in a separate github repository with respect to the aiida-yambo plugin. 
You should clone the [tutorials-aiida-yambo](https://github.com/mikibonacci/tutorials-aiida-yambo) repository, to have access to the notebook.
:::
- AiiDA and aiida-quantumespresso: Ground state properties: 
    - [AiiDA prerequisite](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/prerequisites/0_1_structure_and_pseudos.ipynb): how to set up structures, pseudopotentials and groups in AiiDA;
    - [aiida-quantumespresso prerequisite](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/prerequisites/0_2_QE_starting_point.ipynb): how to run the required DFT starting point (scf+nscf), via the `aiida-quantumespresso` plugin;
- G0W0 and Bethe-Salpeter equation:
    - [Simple yambo calculation](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/1_YamboCalculation_G0W0.ipynb);
    - [Enabling error handling](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/2_YamboRestart_G0W0.ipynb);
    - From scratch to yambo results: DFT+MBPT
        - [One G0W0 calculation](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/3_1_YamboWorkflow_G0W0.ipynb);
        - [Multiple QP calculations](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/3_2_YamboWorkflow_QP.ipynb);
        - [A BSE simulation using scissor&stretching corrections](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/5_1_YamboWorkflow_BSE.ipynb);
        - [A BSE simulation using explicit quasiparticle corrections](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/5_2_YamboWorkflow_BSE_QP.ipynb);
    - Automated convergence of MBPT:
        - [G0W0 case](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/4_YamboConvergence_G0W0.ipynb);
        - [BSE case](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo/6_YamboConvergence_BSE.ipynb);
- aiida-yambo-wannier90: interpolating the G0W0 band structure via Wannierization
    - [W90@QE](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/1_Band_interpolation_W90_DFT.ipynb);
    - [reference QE band structure](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/2_PwBands.ipynb);
    - [Fully automated W90@G0W0 interpolated band structure](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/3_Band_interpolation_W90_G0W0_full.ipynb)
    - [Analysis of W90@G0W0](https://nbviewer.org/github/mikibonacci/tutorials-aiida-yambo/blob/main/yambo_wannier90/Si_analysis.ipynb).

Within the package you can also find example scripts to run each workchain;
these can be found in the examples folder.
