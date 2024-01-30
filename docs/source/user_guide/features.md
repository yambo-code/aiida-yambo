.. _tips:

Tips
====

Settings of a YamboCalculation
------------------------------

The settings Dict that we provide as input of a YamboCalculation can decide the order of p2y and yambo executables. 
To understand the possible actions, we need to explain how the plugin works in the four standard cases.

The plugin currently supports four types of logic to run a calculation:

1) p2y and yambo initialization from NSCF
     this will just run a p2y+yambo calculation to create the Yambo SAVE database and initialise it. Before the p2y+yambo run, the nscf save folder is copied into the 
     new remote directory. It is triggered by using as parent calculation an NSCF run with the quantumespresso.pw plugin and by setting:

    ::
        inputs['settings'] = Dict(dict={'INITIALISE': True})
        inputs['parameters'] = Dict(dict={}) #no more needed: we are just running a p2y + yambo init

2) yambo from a p2y
    triggered simply by using as parent calculation a p2y run with the yambo plugin. This will, by default, create a link of the SAVE directory 
    contained in the p2y remote folder.

3) p2y + yambo from a NSCF
    triggered by using as parent calculation an NSCF calculation run with the quantumespresso.pw plugin

4) yambo from a (previous) yambo
    useful in particular for restarts, it is triggered by using as parent calculation a Yambo calculation run with the yambo plugin. 

If you want also to link the output databases produced from the previous yambo calculation, you can set:
    
::

    inputs['settings'] = examples_hBN/ground_state/(dict={'COPY_DBS': True})

in this way you can continue your calculation from the last point by hard-copying the output folder of the previous calculation. 
These are the main logics of a typical YamboCalculation. There can be problems in the linking of the SAVE and output directories, so you can tell the plugin to 
make an hard copy of the folder of interest:

::

    inputs['settings'] = Dict(dict={'COPY_SAVE': True})
    

so, a complete settings Dict will be:

::

    inputs['settings'] = Dict(dict={'INITIALISE': True,
                                             'COPY_SAVE': True,
                                             'COPY_DBS': True,
                                             })

Yambo in Parallel 
-----------------

The computational effort done during a Yambo calculation requires an extensive and wise use of parallelization schemes on various quantities
that are computed during the simulation. A tutorial for user-defined parallelism instructions can be found at the [yambo wiki page](http://www.yambo-code.org/wiki/index.php?title=GW_parallel_strategies). In any case, when yambo 
sees a parallelization problem before to start the real calculation, tries to use its default scheme. 

For default yambo parallelizationjust put, in the parameters dictionary, the instruction 
                
```python
'PAR_def_mode': "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")
```


Where are my retrieved files? 
-----------------------------

In the verdi shell, type:

```python
path = load_node(<pk_of_the_calc>).outputs.retrieved._repository._repo_folder.abspath
```

Where is my remote folder? 
--------------------------

In the verdi shell, type:

```python
path = load_node(<pk_of_the_calc>).outputs.remote_folder.get_remote_path()
```

How can I recover a pw calculation from a yambo one? 
----------------------------------------------------

In the verdi shell, type:

```python
from aiida_yambo.utils.common_helpers import find_pw_parent
find_pw_parent(load_node(<pk of the calc>),calc_type=['nscf']) # or 'scf'
```