(user-guide)=

# User guide

In this section we presents several examples on how to run Calcjobs and WorkChains, as well as their description. 
We start from DFT and we go through GW and BSE steps.
For the sake of consistency, we consider the same system as the tutorials, i.e. the bulk hexagonal
Boron Nitride (hBN).

:::{important}
These how-to guides assume you already installed and properly configured AiiDA, Quantum ESPRESSO (and its AiiDA plugin) and Yambo. 
You can check the main [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html), 
[aiida-quantumespresso documentation](https://aiida-quantumespresso.readthedocs.io/en/latest/)
and [yambo-code documentation](https://www.yambo-code.eu) for more information on how to perform these steps.
:::

```{toctree}
:maxdepth: 2

get_started/dft_p2y
get_started/tutorial_gw
workflows/index
```