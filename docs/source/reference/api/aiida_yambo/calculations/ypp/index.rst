:py:mod:`aiida_yambo.calculations.ypp`
======================================

.. py:module:: aiida_yambo.calculations.ypp

.. autoapi-nested-parse::

   Plugin to create a YPP input file and run a calculation with the ypp executable.



Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.calculations.ypp.YppCalculation




Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.calculations.ypp.PwCalculation
   aiida_yambo.calculations.ypp.YamboCalculation
   aiida_yambo.calculations.ypp.SingleFileData
   aiida_yambo.calculations.ypp.__authors__


.. py:data:: PwCalculation

   

.. py:data:: YamboCalculation

   

.. py:data:: SingleFileData

   

.. py:data:: __authors__
   :value: ' Miki Bonacci (miki.bonacci@unimore.it), Nicola Spallanzani'

   

.. py:class:: YppCalculation(*args, **kwargs)


   Bases: :py:obj:`aiida.engine.CalcJob`

   AiiDA plugin for the Ypp code.
   For more information, refer to http://www.yambo-code.org/
   https://github.com/yambo-code/yambo-aiida and http://aiida-yambo.readthedocs.io/en/latest/

   .. py:attribute:: _DEFAULT_INPUT_FILE
      :value: 'ypp.in'

      

   .. py:attribute:: _DEFAULT_OUTPUT_FILE
      :value: 'aiida.out'

      

   .. py:method:: define(spec)
      :classmethod:

      Define the process specification, including its inputs, outputs and known exit codes.

      Ports are added to the `metadata` input namespace (inherited from the base Process),
      and a `code` input Port, a `remote_folder` output Port and retrieved folder output Port
      are added.

      :param spec: the calculation job process spec to define.


   .. py:method:: prepare_for_submission(tempfolder)

      Prepare the calculation for submission.

      Convert the input nodes into the corresponding input files in the format that the code will expect. In addition,
      define and return a `CalcInfo` instance, which is a simple data structure that contains  information for the
      engine, for example, on what files to copy to the remote machine, what files to retrieve once it has completed,
      specific scheduler settings and more.

      :param folder: a temporary folder on the local file system.
      :returns: the `CalcInfo` instance



