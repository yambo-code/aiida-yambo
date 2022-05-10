.. _tut-ref-to-yambo-wfl:

YamboWorkflow for GW/BSE
--------------------

The `YamboWorkflow`  provides the functionality to run GW calculation from the pw-DFT step, passing in all the required
parameters for both the KS-DFT steps, scf and nscf, and the subsequent GW step. It uses the PwBaseWorkchain from `aiida-quantumespresso`
as a subworkflow to perform the first DFT part, if required, and the `YamboRestart` for the GW part. A smart logic is considered to understand what 
process has to be done to achieve success. If the previous calculation is not ``finished_ok``, the workflow will exit in a failed state: we suppose that 
the success of an input calculation is guaranteed by the RestartWorkchain used at the lower level of the plugin. 

Example usage.

.. include:: ../../../../examples/test_wf/yambo_workflow.py
   :literal:

As you may notice, here the builder has a new attributes, referring to scf, nscf and yambo parts: this means that we are actually providing the inputs for 
respectively PwBaseWorkchain and YamboRestart. 
The only 'strict' YamboWorkflow input is now the ``parent_folder``. 
Moreover, it is possible to ask the workflow to compute and parse some specific quantities, like gaps and quasiparticle levels. This is possible by providing as input an `additional parsing list`:

::
   
   builder.additional_parsing = List(list=['gap_',])

In this way, the workflow will first analyze the nscf calculation, understand where the gap is and then modify the YamboRestart inputs in such a way to have computed the corresponding gap at the GW level.
Then, the quantity is stored in a human-readable output Dict called `output_ywfl_parameters`.
In case of BSE calculation, we can ask in the additional parsing list for the lowest and/or the brightest excitons. If you have the ndb.QP (as SingleFileData, output of a YamboCalculation for example), you can provide as 
input to the workflow and so run BSE on top of this database. See the example for a clear explanation of the inputs needed.

YamboWorkflow for GW + QP calculations
--------------------------------------

Another quantity that we can compute within the `YamboWorkflow` is a set of QP evaluations. This may be needed for band interpolation or for BSE calculations. It is possible to instruct the worlkflow to add 
this step by providing as input 

::

   builder.QP_subset_dict= Dict(dict={
                                            'qp_per_subset':20,
                                            'parallel_runs':4,
                                            'range_QP':5,
                                            'full_bands':True,
    })

to compute all the QP around 5 eV of the Fermi level (in case of semiconductors) and for each k-point of the iBZ (full bands = True), or, to compute some explicit QP: 

::

   builder.QP_subset_dict= Dict(dict={
                                            'qp_per_subset':20,
                                            'parallel_runs':4,
                                            'explicit':[[k1,k2,b1,b2],...],
    })

So that 20 `YamboRestart` are performed at the same time, each of them computing 20 QP eigenvalues. Then at the end of the calculations the ndb.QP databases are merged in only one database and exposed as a SingleFileData 
output (``merged_QP``). The merging is done by using yambopy functionalities. 

YamboWorkflow for BSE on top of QP
----------------------------------

It is possible also to ask the `YamboWorkflow` to run BSE on top of a QP database not yet computed. A first GW QP calculation is done, and then the workflow understand, if not provided, what Q-index is needed to compute the 
excitonic properties. 

Example usage.

.. include:: ../../../../examples/test_wf/yambo_workflow_QP_BSE.py
   :literal:
