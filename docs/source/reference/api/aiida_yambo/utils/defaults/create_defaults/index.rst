:py:mod:`aiida_yambo.utils.defaults.create_defaults`
====================================================

.. py:module:: aiida_yambo.utils.defaults.create_defaults

.. autoapi-nested-parse::

   default input creation



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.defaults.create_defaults.periodical
   aiida_yambo.utils.defaults.create_defaults.create_quantumespresso_inputs



Attributes
~~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.defaults.create_defaults.scf
   aiida_yambo.utils.defaults.create_defaults.nscf
   aiida_yambo.utils.defaults.create_defaults.periodic_table


.. py:data:: scf

   

.. py:data:: nscf

   

.. py:data:: periodic_table

   

.. py:function:: periodical(structure)


.. py:function:: create_quantumespresso_inputs(structure, bands_gw=None, spin_orbit=False, what=['scf', 'nscf'])

   with open('./scf_qe_default.json','r') as file:
       scf = json.load(file)
   with open('./nscf_qe_default.json','r') as file:
       nscf = json.load(file)


