---
myst:
  substitutions:
    aiida-core documentation: '`aiida-core` documentation'
    aiida-yambo: '`aiida-yambo`'
    AiiDA: '[AiiDA](http://www.aiida.net)'
    yambo-code: '[yambo-code](https://www.yambo-code.eu)'
---

```{toctree}
:hidden: true

installation/index
```

```{toctree}
:hidden: true

user_guide/index
```

# Welcome to the documentation of the *aiida-yambo* package!

`AiiDA Yambo` is a package that allows to automate many-body perturbation theory calculations using the [yambo-code](https://www.yambo-code.eu) in the AiiDA framework.
Currently, the aiida-yambo plugin supports 
quasiparticle (G0W0, COSHEX and HFlevel) 
and optical properties (IP-RPA and BSE) simulations, 
as well as interfaces with different codes (e.g., Quantum ESPRESSO and Wannier90).

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} {fa}`rocket;mr-1` Get started
:text-align: center
:shadow: md

Instructions to install, configure and setup the plugin package.

+++

```{button-ref} installation/index
:ref-type: doc
:click-parent:
:expand:
:color: primary
:outline:

To the installation section
```
:::

:::{grid-item-card} {fa}`info-circle;mr-1` User guide
:text-align: center
:shadow: md

Consult the user guide and tutorials.

+++

```{button-ref} user_guide/index
:ref-type: doc
:click-parent:
:expand:
:color: primary
:outline:

To the user guide and tutorials
```
:::

::::

# How to cite

If you use this package for your research, please cite the following works:

> M. Bonacci, J. Qiao , N. Spallanzani, A. Marrazzo, G. Pizzi, E. Molinari, D. Varsano, A. Ferretti, D. Prezzi, [*Towards high-throughput many-body perturbation theory: efficient algorithms and automated workflows*](https://www.nature.com/articles/s41524-023-01027-2), npj Computational Materials, **9**, 74 (2023).

> D. Sangalli, A. Ferretti, H. Miranda, C. Attaccalite, I. Marri, E. Cannuccia, P. Melo, M. Marsili, F. Paleari, A. Marrazzo, G. Prandini, P. Bonfà, M.O. Atambo, F. Affinito, M. Palummo, A. Molina-Sánchez, C. Hogan, M. Grüning, D. Varsano, A. Marini, [*Many-body perturbation theory calculations using the yambo code*](https://doi.org/10.1088/1361-648X/ab15d0), J. Phys. Condens. Matter, **31**, 325902 (2019).

> S. P. Huber, S. Zoupanos, M. Uhrin, L. Talirz, L. Kahle, R. H ̈auselmann, D. Gresch, T. M ̈uller, A. V. Yakutovich, C. W. Andersen, F. F. Ramirez, C. S. Adorf, F. Gargiulo, S. Kumbhar, E. Passaro, C. Johnston, A. Merkys, A. Cepellotti, N. Mounet, N. Marzari, B. Kozinsky, and G. Pizzi, [*AiiDA 1.0, a scalable computational infrastructure for automated reproducible workflows and data provenance*](https://www.nature.com/articles/s41597-020-00638-4), Sci. Data **7**, 300 (2020).

> Martin Uhrin, Sebastiaan. P. Huber, Jusong Yu, Nicola Marzari, and Giovanni Pizzi, [*Workflows in AiiDA: Engineering a high-throughput, event-based engine for robust and modular computational workflows*](https://doi.org/10.1016/j.commatsci.2020.110086), Computational Materials Science **187**, 110086 (2021)

> G. Pizzi, A. Cepellotti, R. Sabatini, N. Marzari, and B. Kozinsky, [*AiiDA: automated interactive infrastructure and database for computational science*](http://dx.doi.org/10.1016/j.commatsci.2015.09.013), Comp. Mat. Sci **111**, 218-230 (2016).


Acknoledgements
===============

This work was supported by: the Centre of Excellence "MaX - Materials Design at the Exascale" funded by European Union 
(H2020-EINFRA-2015-1, Grant No. 676598; H2020-INFRAEDI-2018-1, Grant No. 824143; HORIZON-EUROHPC-JU-2021-COE-1 , 
Grant No. 101093374); the European Union's Horizon 2020 research and innovation programme 
(BIG-MAP, Grant No. 957189, also part of the BATTERY 2030+ initiative, Grant No. 957213); 
NCCR MARVEL, a National Centre of Competence in Research, funded by the Swiss National Science 
Foundation (Grant No. 205602).


<img src="images/cropped-cropped-logo-MAX-orizz-300.png" alt="MaX-logo" width="350" height="110">

<img src="images/battery2030_reduced.png" alt="battery2030-logo" width="340" height="170">

<img src="images/bigmap_logo.png" alt="BigMap-logo" width="230" height="230">

<img src="images/s3center.png" alt="S3-logo" width="150" height="150">

<img src="images/Flag_of_Europe.png" alt="Eu-flag" width="250" height="170">

<img src="images/MARVEL.png" alt="MARVEL-logo" width="150" height="150">
