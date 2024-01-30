:py:mod:`aiida_yambo.parsers.ext_dep.yambofile`
===============================================

.. py:module:: aiida_yambo.parsers.ext_dep.yambofile


Module Contents
---------------

Classes
~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.ext_dep.yambofile.YamboFile



Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.ext_dep.yambofile.if_has_netcdf



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.ext_dep.yambofile._has_netcdf


.. py:data:: _has_netcdf
   :value: False

   

.. py:function:: if_has_netcdf(f)


.. py:class:: YamboFile(filename, folder='.')


   Bases: :py:obj:`object`

   This is the Yambo file class.
   It takes as input a filename produced by yambo.
   Can be a netcdf or a text file

   List of supported NETCDF files:
       -> ndb.QP

   List of supported text files:
       -> r-*_em?1_*_gw0
       -> o-*.qp

   .. py:attribute:: _output_prefixes
      :value: ['o-']

      

   .. py:attribute:: _report_prefixes
      :value: ['r-', 'r.']

      

   .. py:attribute:: _log_prefixes
      :value: ['l-', 'l_', 'l.']

      

   .. py:attribute:: _netcdf_prefixes
      :value: ['ns', 'ndb']

      

   .. py:attribute:: _netcdf_sufixes

      

   .. py:attribute:: __nonzero__

      

   .. py:method:: get_filetype(filename, folder)
      :staticmethod:

      Get the type of file


   .. py:method:: parse()

      Parse the file
      Add here things to read log and report files...


   .. py:method:: parse_output()

      Parse an output file from yambo,
              


   .. py:method:: parse_netcdf_gw()

      Parse the netcdf gw file
              


   .. py:method:: parse_netcdf_hf()

      Parse the netcdf hf file (ndb.HF_and_locXC)
              


   .. py:method:: parse_report()

      Parse the report files.
      produces output of this nature:
      { k-index1  : { 'dft_enrgy':[...], 'qp_energy':[...] },
        k-index2  :{...}
      }
      k-index is the kpoint at which the yambo calculation was
      done.


   .. py:method:: get_type()

      Get the type of file
              


   .. py:method:: has_errors()


   .. py:method:: get_errors()

      Check if this is a report file and if it contains errors
              


   .. py:method:: get_data()

      Get the data from this file as a dictionary
              


   .. py:method:: parse_log()

      Get ERRORS and WARNINGS from  l-*  file, useful for debugging
              


   .. py:method:: __bool__()


   .. py:method:: __str__()

      Return str(self).



