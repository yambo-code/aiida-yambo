:py:mod:`aiida_yambo.utils.common_helpers`
==========================================

.. py:module:: aiida_yambo.utils.common_helpers

.. autoapi-nested-parse::

   helpers for many purposes



Module Contents
---------------


Functions
~~~~~~~~~

.. autoapisummary::

   aiida_yambo.utils.common_helpers.find_parent
   aiida_yambo.utils.common_helpers.find_pw_parent
   aiida_yambo.utils.common_helpers.old_find_parent
   aiida_yambo.utils.common_helpers.old_find_pw_parent
   aiida_yambo.utils.common_helpers.get_distance_from_kmesh
   aiida_yambo.utils.common_helpers.find_pw_type
   aiida_yambo.utils.common_helpers.find_table_ind
   aiida_yambo.utils.common_helpers.update_dict
   aiida_yambo.utils.common_helpers.get_caller
   aiida_yambo.utils.common_helpers.get_called
   aiida_yambo.utils.common_helpers.set_parent
   aiida_yambo.utils.common_helpers.take_down
   aiida_yambo.utils.common_helpers.take_super
   aiida_yambo.utils.common_helpers.take_calc_from_remote
   aiida_yambo.utils.common_helpers.take_fermi
   aiida_yambo.utils.common_helpers.take_filled_states
   aiida_yambo.utils.common_helpers.take_number_kpts
   aiida_yambo.utils.common_helpers.store_List
   aiida_yambo.utils.common_helpers.store_Dict
   aiida_yambo.utils.common_helpers.find_pw_info
   aiida_yambo.utils.common_helpers.find_gw_info
   aiida_yambo.utils.common_helpers.understand_valence_metal_wise
   aiida_yambo.utils.common_helpers.build_list_QPkrange
   aiida_yambo.utils.common_helpers.gap_mapping_from_nscf
   aiida_yambo.utils.common_helpers.check_identical_calculation
   aiida_yambo.utils.common_helpers.check_same_yambo
   aiida_yambo.utils.common_helpers.check_same_pw
   aiida_yambo.utils.common_helpers.search_in_group
   aiida_yambo.utils.common_helpers.store_quantity



.. py:function:: find_parent(calc)


.. py:function:: find_pw_parent(parent_calc, calc_type=['scf', 'nscf'])


.. py:function:: old_find_parent(calc)


.. py:function:: old_find_pw_parent(parent_calc, calc_type=['scf', 'nscf'])


.. py:function:: get_distance_from_kmesh(calc)


.. py:function:: find_pw_type(calc)


.. py:function:: find_table_ind(kpoint, band, _array_ndb)


.. py:function:: update_dict(_dict, whats, hows, sublevel=None, pop_list=[])


.. py:function:: get_caller(calc_pk, depth=1)


.. py:function:: get_called(calc_pk, depth=2)


.. py:function:: set_parent(inputs, parent)


.. py:function:: take_down(node=0, what='CalcJobNode')


.. py:function:: take_super(node=0, what='WorkChainNode')


.. py:function:: take_calc_from_remote(parent_folder, level=0)


.. py:function:: take_fermi(calc_node_pk)


.. py:function:: take_filled_states(calc_node_pk)


.. py:function:: take_number_kpts(calc_node_pk)


.. py:function:: store_List(a_list)


.. py:function:: store_Dict(a_dict)


.. py:function:: find_pw_info(calc)


.. py:function:: find_gw_info(inputs)


.. py:function:: understand_valence_metal_wise(bands, fermi, index, valence)


.. py:function:: build_list_QPkrange(mapping, quantity, nscf_pk, bands, fermi, valence)


.. py:function:: gap_mapping_from_nscf(nscf_pk, additional_parsing_List=[])


.. py:function:: check_identical_calculation(YamboWorkflow_inputs, YamboWorkflow_list, what=['BndsRnXp', 'GbndRnge', 'NGsBlkXp'], full=True, exclude=['CPU', 'ROLEs', 'QPkrange'])


.. py:function:: check_same_yambo(node, params_to_calc, k_mesh_to_calc, what, up_to_p2y=False, full=True, additional=[], bands=None)


.. py:function:: check_same_pw(node, k_mesh_to_calc, already_done, bands=None)


.. py:function:: search_in_group(YamboWorkflow_inputs, YamboWorkflow_group, what=['BndsRnXp', 'GbndRnge', 'NGsBlkXp'], full=True, exclude=[], up_to_p2y=False, bands=None)


.. py:function:: store_quantity(quantity)


