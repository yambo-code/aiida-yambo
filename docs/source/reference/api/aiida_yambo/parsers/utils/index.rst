:py:mod:`aiida_yambo.parsers.utils`
===================================

.. py:module:: aiida_yambo.parsers.utils


Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.utils.take_fermi_parser
   aiida_yambo.parsers.utils.yambotiming_to_seconds
   aiida_yambo.parsers.utils.parse_log
   aiida_yambo.parsers.utils.parse_report
   aiida_yambo.parsers.utils.parse_scheduler_stderr
   aiida_yambo.parsers.utils.yambo_wrote_dbs
   aiida_yambo.parsers.utils.get_yambo_version
   aiida_yambo.parsers.utils.parse_BS



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.parsers.utils.errors
   aiida_yambo.parsers.utils.errors_raw


.. py:function:: take_fermi_parser(file)


.. py:function:: yambotiming_to_seconds(yt)


.. py:data:: errors

   

.. py:data:: errors_raw

   

.. py:function:: parse_log(log, output_params, timing)


.. py:function:: parse_report(report, output_params)


.. py:function:: parse_scheduler_stderr(stderr, output_params)


.. py:function:: yambo_wrote_dbs(output_params)


.. py:function:: get_yambo_version(report, output_params)


.. py:function:: parse_BS(folder, filename, save_dir)


