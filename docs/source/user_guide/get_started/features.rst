.. _2-ref-to-yambo-tutorial:

Settings of a YamboCalculation
------------------------------

The settings Dict that we provide as input of a YamboCalculation is a fundamental quantity that can decide the logic of pre-yambo executable action that are accomplished 
by the plugin. To understand the possible actions, we need to explain how the plugin works in standard cases.

The plugin currently supports, four type of logic to run a calculation:

**p2y from a NSCF**: this will just run a p2y calculation to create the Yambo SAVE database, before to run, the nscf save folder is copied to the 
                       new remote directory. It is triggered by using as parent calculation an NSCF run with the quantumespresso.pw plugin and by setting:

::
    
    inputs['settings'] = ParameterData(dict={'INITIALISE': True})


**yambo from a p2y**: triggered simply by using as parent calculation a p2y run with the yambo plugin. This will, by default, create a link of the SAVE directory 
                      contained in the p2y remote folder.
**p2y + yambo from a NSCF**: triggered by using as parent calculation an NSCF calculation run with the quantumespresso.pw plugin
**yambo from a (previous) yambo: useful in particular for restarts, it is triggered by using as parent calculation a Yambo calculation run with the yambo plugin. 
                                    If you want also to link the output databases produced from the previous yambo calculation, you can set:
    
::

    inputs['settings'] = ParameterData(dict={'RESTART_YAMBO': True})

in this way you can continue your calculation from the last point. 
These are the main logics of a typical YamboCalculation. There can be problems in the linking of the SAVE and output directories, so you can tell the plugin to 
make an hard copy of the folder of interest:

::

    inputs['settings'] = ParameterData(dict={'COPY_SAVE': True})
    inputs['settings'] = ParameterData(dict={'COPY_DBS': True})

so, a complete settings Dict will be:

::

    inputs['settings'] = ParameterData(dict={'INITIALISE': True,
                                             'RESTART_YAMBO': True,
                                             'COPY_SAVE': True,
                                             'COPY_DBS': True,
                                             })

Primer on Yambo parallelizations 
--------------------------------

The computational effort done during a Yambo calculation requires an extensive and wise use of parallelization schemes on various quantities
that are computed during the simulation. There are two ways to find an automatic parallelization scheme in the AiiDA-yambo 
plugin: to use predefined Yambo-core parallelization utilities or to use the parallelizer provided in the plugin. 

**default yambo parallelization**: just put, in the parameters dictionary, the instruction 
                
::

    PAR_def_mode= "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")

**yambo-aiida parallelizer**: you can choose the roles to be parallelized between bands or kpoints, or both; this may modify your resources by 
                               fitting them to the dimensions of the simulation, but only changing mpi-openmpi balance or reducing the total 
                               number of processors if they are too much (example: you may want parallelize 100 bands with 150 CPUs -> reduce CPUs 
                               to 100)

To use the plugin parallelizer:

::

    from aiida_yambo.utils.parallelism_finder import *
    
    find_parallelism_qp(nodes, mpi_per_node, threads, bands, occupied=2, qp_corrected=2, kpoints = 1, \
                        what = ['bands'], last_qp = 2)

the input ``what`` is a list of what you want to parallelize:``bands,kpoints``. You have also to provide some useful information like the computational
resources, the total number of bands that you have in the simulation, the occupied states, and so on. 