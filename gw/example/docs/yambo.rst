GW
++

Description
-----------
Plugin that provides support for running GW calcualtion with the Yambo code 

Supported codes
---------------
Support for the 3.4x upto 4.x Yambo versions  is currently implemented.


Inputs
------
* **parameters**, class :py:class:`ParameterData <aiida.orm.data.parameter.ParameterData>`
  Yambo input parameters, in the form of a dictionary, matching the Yambo input 
  Example::

              {
              'ppa': True,
              'gw0': True,
              'rim_cut': True,
              'HF_and_locXC': True,
              'em1d': True,
              'X_all_q_CPU': "1 2 8 2",
              'X_all_q_ROLEs': "q k c v",
              'X_all_q_nCPU_invert':0,
              'X_Threads':  1 ,
              'DIP_Threads': 1 ,
              'SE_CPU': "1 4 8",
               }

* **settings**, class :py:class:`ParameterData <aiida.orm.data.parameter.ParameterData>` (optional)
  An optional dictionary that activates non-default operations. For a list of possible
  values to pass, see the section on the :ref:`advanced features <yambo-advanced-features>`.
    
* **parent_folder**, class :py:class:`RemoteData <aiida.orm.data.parameter.ParameterData>` (Required)
  This is the scratch directory from the preceeding PW calculations, required to generate Yambo 
  databases and initialize the calculation.


Outputs
-------

There are several output nodes that can be created by the plugin, according to the calculation details.
All output nodes can be accessed with the ``calculation.out`` method.

* output_parameters :py:class:`ParameterData <aiida.orm.data.parameter.ParameterData>` 
  Contains warnings and errors, no calculation data is stored in the output_parameter.

* output_array :py:class:`ArrayData <aiida.orm.data.array.ArrayData>`
  Several named output_array's are produced depending on the Yambo calculation, these include:
  `array_qp` for COHSEX and G0W0 calculations, `bands_quasiparticle` for  quasiparticle calculations.
  The corresponing output files need be retreived for these arrays to be stored, these include the `ndb.QP`
  `ndb.HF_and_LOCXC` yambo report files and any   `*.QP`. 


Errors and Warnings
--------------------
Errors and warnings of the calculation are stored under the key ``warnings`` in the output dict.

.. _yambo-advanced-features:

Additional advanced features
----------------------------


Retrieving more files
.....................
The files to be retrieved after a calculation are set by adding them to the settings::

  settings_dict = {  
     "ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01']
     }


