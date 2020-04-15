.. _2-ref-to-yambo-tutorial:

Settings of a YamboCalculation
------------------------------

The settings Dict that we provide as input of a YamboCalculation is a fundamental quantity that can decide the logic of pre-yambo executable action that are accomplished 
by the plugin. To understand the possible actions, we need to figure out how the plugin works in the standard case.

The plugin currently supports, three type of logic to run a calculation:

- **p2y from a NSCF**: this will just run a p2y calculation to create the Yambo SAVE database, before to run, the nscf save folder is copied to the 
                       new remote directory. It is triggered by using as parent calculation an NSCF run with the quantumespresso.pw plugin and by setting:

    inputs['settings'] = ParameterData(dict={'INITIALISE': True}) )


- **yambo from a p2y**: triggered simply by using as parent calculation a p2y run with the yambo plugin (as explained above in the option **p2y from a NSCF**)
- **p2y + yambo from a NSCF**: triggered by using as parent calculation an NSCF calculation run with the quantumespresso.pw plugin
- **yambo from a (previous) yambo**: useful in particular for restarts, it is triggered by using as parent calculation a Yambo calculation run with the yambo plugin. If you want also to copy the output databases produced from the previous yambo calculation,
  you can set:
    
    inputs['settings'] = ParameterData(dict={'PARENT_DB': True}) )


Primer on Yambo parallelizations 
--------------------------------

The computational effort done during a Yambo calculation implies an extensive and wise use of parallelization schemes on various quantities
that are computed during the simulation. There are two ways to find an automatic parallelization scheme in the AiiDA-yambo 
plugin: to use predefined Yambo-core parallelization utilities or to use the parallelizer provided in the plugin. 
