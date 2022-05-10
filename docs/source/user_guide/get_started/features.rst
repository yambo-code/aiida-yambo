.. _tips:

Settings of a YamboCalculation
------------------------------

The settings Dict that we provide as input of a YamboCalculation is a fundamental quantity that can decide the logic of pre-yambo executable action that are accomplished 
by the plugin. To understand the possible actions, we need to explain how the plugin works in standard cases.

The plugin currently supports four type of logic to run a calculation:

1) p2y from a NSCF
     this will just run a p2y calculation to create the Yambo SAVE database, before to run, the nscf save folder is copied to the 
     new remote directory. It is triggered by using as parent calculation an NSCF run with the quantumespresso.pw plugin and by setting:

    ::
    
        inputs['settings'] = ParameterData(dict={'INITIALISE': True})


2) yambo from a p2y
    triggered simply by using as parent calculation a p2y run with the yambo plugin. This will, by default, create a link of the SAVE directory 
    contained in the p2y remote folder.

3) p2y + yambo from a NSCF
    triggered by using as parent calculation an NSCF calculation run with the quantumespresso.pw plugin

4) yambo from a (previous) yambo
    useful in particular for restarts, it is triggered by using as parent calculation a Yambo calculation run with the yambo plugin. 

If you want also to link the output databases produced from the previous yambo calculation, you can set:
    
::

    inputs['settings'] = ParameterData(dict={'COPY_DBS': True})

in this way you can continue your calculation from the last point by hard-copying the output folder of the previous calculation. 
These are the main logics of a typical YamboCalculation. There can be problems in the linking of the SAVE and output directories, so you can tell the plugin to 
make an hard copy of the folder of interest:

::

    inputs['settings'] = ParameterData(dict={'COPY_SAVE': True})
    

so, a complete settings Dict will be:

::

    inputs['settings'] = ParameterData(dict={'INITIALISE': True,
                                             'COPY_SAVE': True,
                                             'COPY_DBS': True,
                                             })

Primer on Yambo parallelizations 
--------------------------------

The computational effort done during a Yambo calculation requires an extensive and wise use of parallelization schemes on various quantities
that are computed during the simulation. A tutorial for user-defined parallelism instructions can be found at http://www.yambo-code.org/wiki/index.php?title=GW_parallel_strategies. In any case, when yambo 
sees a parallelization problem before to start the real calculation, tries to use its default scheme. 

**default yambo parallelization**: 

    just put, in the parameters dictionary, the instruction 
                
    ::

        'PAR_def_mode': "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")