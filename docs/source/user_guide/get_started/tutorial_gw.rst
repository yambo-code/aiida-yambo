.. _sec.yambo_calc_plugin:

.. _my-ref-to-yambo-tutorial:

G0W0 calculations
=================

.. toctree::
   :maxdepth: 2

Setting up the first G0W0 calculation
-------------------------------------

Once completed the preliminary steps, we are ready to run a G0W0 calculation in the common Godby-Needs plasmon-pole approximation (PPA).
In particular we compute the direct band gap at Gamma of hBN. The core of the inputs are the parameters, which will be written in the input file 
that is used to feed the yambo executable. 

.. include:: ../../../../examples/plugin/yambo_gw.py
   :literal:

The quasiparticle corrections and the renormalization factors can be accessed from the Yambo calculation (yambo_calc) using the output bands and array data:

::

	yambo_calc = load_node(pk)
	energies_DFT = yambo_calc.outputs.array_ndb.get_array('E_0')
	QP_corrections =  yambo_calc.outputs.array_ndb.get_array('E_minus_Eo')
	Z_factors =  yambo_calc.outputs.array_ndb.get_array('Z')
	kpoint_band_array = yambo_calc.outputs.array_ndb.get_array('qp_table')
	kpoints = y.outputs.bands_quasiparticle.get_kpoints()



To retrieve additional files, you can provide their names in the input settings Dict:

::

    settings = ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01',
                        'aiida.out/ndb.QP','aiida.out/ndb.HF_and_locXC']})
    builder.use_settings(settings)

This selects the additional files that will  be retrieved and parsed after a calculation. Supported
files include the report files ``r-*``, text outputs ``o-*``, logs, the quasiparticle
database for GW calculations ``aiida.out/ndb.QP``, and the Hartree-Fock and local exchange
db ``aiida.out/ndb.HF_and_locXC``. Actually, all the files above are automatically collected from the plugin: quantities
that you may want collect to further analyse are for example the dipoles or the dielectric function databases, produced in a typical GW
calculation.
