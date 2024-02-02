(yamborestart)=

# YamboRestart

This is the lowest-level workchain delivered within the plugin, and submits a single yambo calculation, wrapping the YamboCalculation class.
A restart logic is implemented, with a tolerance for failed calculations due to

- Time Exhaustion on the queue: run a new calculation with 50% more time and copying the partial results obtained in the failed one.
- Parallization errors: use the built-in parallelizer to attempt a fixing.
- Corruption of databases: it just restart the calculation deleting the corrupted files but copying all the other outputs, for an efficient restart.
- Memory errors: reduce mpi(/2) and increase threads(*2) to attempt a better memory distribution. Redefine parallelism options settings defaults. It can increase resources only if mpi = 1 or if the number of maximum nodes provided 
  as input is not yet reached.

After each calculation, this workflow will check the exit status (provided by means of the yambo parser) and, if the calculation is failed,
YamboRestart will try to fix some parameters/settings in order to resubmit the calculation and obtain meaningful results. As inputs, we have to provide
the maximum number of iterations that the workchain will perform (defaults is 5).
The YamboRestart inherits the BaseRestartWorkchain class contained in the aiida-core package. 
This enables a lot the error detection/handling 
mechanisms, and provides a unified restart logic for all the AiiDA plugins.

As in a YamboCalculation, you have to provide all the necessary inputs, paying attention to the 
fact that now the builder has the attribute 'yambo' for the variables that refers to YamboCalculation sub-inputs of the workchain.
The only exception is the 'parent_folder', that is provided as direct YamboRestart input for simplicity.
Novel YamboRestart inputs, with respect to YamboCalculation, are:

```python
builder.max_walltime #max_walltime for a given machine/cluster
builder.max_number_of_nodes #max_number_of_nodes for a given run
builder.max_iterations #from BaseRestartWorkchain: maximum number of attempt to succesfully done the calculation.
builder.clean_workdir #from BaseRestartWorkchain: If `True`, work directories of all called calculation jobs will be cleaned at the end of execution.
```

An example of typical script to run a YamboRestart workchain for hBN is provided in aiida_yambo/examples_hBN/workflows/yambo_restart.py:

Outputs are inherithed from the YamboCalculation.