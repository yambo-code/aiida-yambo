.. _tut-ref-to-yambo-wfl:

YamboWorkflow
--------------

The `YamboWorkflow`  provides the functionality to run GW calculation from the pw-DFT step, passing in all the required
parameters for both the KS-DFT steps, scf and nscf, and the subsequent GW step. It uses the PwBaseWorkchain from `aiida-quantumespresso`
as a subworkflow to perform the first DFT part, if required, and the `YamboRestart` for the GW part. A smart logic is considered to understand what 
process has to be done to achieve success. If the previous calculation is not ``finished_ok``, the workflow will exit in a failed state: we suppose that 
the success of an input calculation is guaranteed by the RestartWorkchain used at the lower level of the plugin. 

Example usage.

.. include:: ../../../../examples/test_wf/yambo_wfl.py
   :literal:

As you may notice, here the builder has a new attributes, referring to scf, nscf and yambo parts: this means that we are actually providing the inputs for 
respectively PwBaseWorkchain and YamboRestart. 
The only 'pure' YamboWorkflow input is now the ``parent_folder``. 