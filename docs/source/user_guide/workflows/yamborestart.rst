.. _tut-ref-to-yambo-res:

YamboRestart
------------

This is the basic workflow and will run a single yambo calculation, wrapping the YamboCalculation class.
The adding values is a restart logic, with a tolerance for failed calculations due to

- Time Exhaustion on the queue: run a new calculation with 50% more time and copying the partial results obtained in the failed one.
- Parallization errors: use the built-in parallelizer to attempt a fixing.
- Memory errors: reduce mpi(/2) and increase threads(*2) to attempt a better memory distribution. Redefine parallelism options with the parallelizer. It can increase resources only if mpi = 1.

After each calculation, this workflow will check the exit status(provided by the parser) and, if the calculation is failed,
try to fix some parameters in order to resubmit the calculation and obtain results. As inputs, we have to provide
the maximum number of iterations that the workchain will perform.
The YamboRestart inherits the BaseRestartWorkchain class, as included in the aiida-core package. This simplifies a lot the error detection/handling 
mechanisms and provides a unified restart logic for all the AiiDA plugins.

As in a YamboCalculation, you have to provide all the necessary inputs, paying attention to the 
fact that now the builder has the attribute 'yambo' for the variables that refers to YamboCalculation part of the workchain.
The only exception is the 'parent_folder', that is provided as direct YamboRestart input.
Other common YamboRestart inputs are:

::
   
   builder.max_walltime #max_walltime for a given machine/cluster
   builder.max_iterations #from BaseRestartWorkchain: maximum number of attempt to succesfully done the calculation.
   builder.clean_workdir #from BaseRestartWorkchain: If `True`, work directories of all called calculation jobs will be cleaned at the end of execution.


Here an example of typical script to run a YamboRestart workchain:

.. include:: ../../../../examples/test_wf/yambo_restart.py
   :literal:

the outputs inherithed from the YamboCalculation.