:py:mod:`aiida_yambo.parsers.parsers`
=====================================

.. py:module:: aiida_yambo.parsers.parsers


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.parsers.YamboParser




Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.parsers.SingleFileData
   aiida_yambo.parsers.parsers.__copyright__
   aiida_yambo.parsers.parsers.__license__
   aiida_yambo.parsers.parsers.__version__
   aiida_yambo.parsers.parsers.__authors__


.. py:data:: SingleFileData

   

.. py:data:: __copyright__
   :value: 'Copyright (c), 2014-2015, École Polytechnique Fédérale de Lausanne (EPFL), Switzerland,...'

   

.. py:data:: __license__
   :value: 'Non-Commercial, End-User Software License Agreement, see LICENSE.txt file'

   

.. py:data:: __version__
   :value: '0.4.1'

   

.. py:data:: __authors__
   :value: (' Miki Bonacci (miki.bonacci@unimore.it), Gianluca Prandini (gianluca.prandini@epfl.ch), Antimo...

   

.. py:class:: YamboParser(calculation)


   Bases: :py:obj:`aiida.parsers.parser.Parser`

   This class is a wrapper class for the Parser class for Yambo calculators from yambopy.

   *IMPORTANT:* This plugin can parse netcdf files produced by yambo if the
   python netcdf libraries are installed, otherwise they are ignored.
   Accepts data from yambopy's YamboFolder  as a list of YamboFile instances.
   The instances of YamboFile have the following attributes:

   ::
     .data: A Dict, with k-points as keys and  in each futher a dict with obeservalbe:value pairs ie. { '1' : {'Eo': 5, 'B':1,..}, '15':{'Eo':5.55,'B': 30}... }
     .warnings:     list of strings, one warning  per string.
     .errors:       list of errors, one error per string.
     .memory        list of string, info on memory allocated and freed
     .max_memory    maximum memory allocated or freed during the run
     .last_memory   last memory allocated or freed during the run
     .last_memory_time   last point in time at which  memory was  allocated or freed
     .*_units       units (e.g. Gb or seconds)
     .wall_time     duration of the run (as parsed from the log file)
     .last_time     last time reported (as parsed from the log file)
     .kpoints: When non empty is a Dict of kpoint_index: kpoint_triplet values i.e.                  { '1':[0,0,0], '5':[0.5,0.0,5] .. }
     .type:   type of file accordParseing to YamboFile types include:
     1. 'report'    : 'r-..' report files
     2. 'output_gw'  : 'o-...qp': quasiparticle output file   ...           .. etc
     N. 'unknown' : when YamboFile was unable to deduce what type of file
     .timing: list of timing info.

   Saved data:

   o-..qp : ArrayData is stored in a format similar to the internal yambo db format (two arrays):
            [[E_o,E-E_o,S_c],[...]]  and
            [[ik,ib,isp],...]
            First is the observables, and the second array contains the kpoint index, band index
            and spin index if spin polarized else 0. BandsData can not be used as the k-point triplets
            are not available in the o-.qp file.

   r-..    : BandsData is stored with the proper list of K-points, bands_labels.


   .. py:method:: parse(retrieved, **kwargs)

      Parses the datafolder, stores results.

      This parser for this code ...


   .. py:method:: _aiida_array_bse(data)


   .. py:method:: _aiida_array(data)


   .. py:method:: _aiida_bands_data(data, cell, kpoints_dict)


   .. py:method:: _aiida_ndb_qp(data)

      Save the data from ndb.QP to the db


   .. py:method:: _aiida_ndb_hf(data)

      Save the data from ndb.HF_and_locXC

              


   .. py:method:: _sigma_c(ndbqp, ndbhf)

      Calculate S_c if missing from  information parsed from the  ndb.*

      Sc = 1/Z[ E-Eo] -S_x + Vxc



