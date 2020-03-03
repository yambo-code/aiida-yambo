.. _sec.yambo_calc_plugin:

.. _my-ref-to-yambo-tutorial:

Yambo-AiiDA  Tutorial
=====================

.. toctree::
   :maxdepth: 2

The following tutorial shows how to run all the necessary steps to obtain a G0W0 result with Yambo for bulk hBN.
In order to keep the tutorial light in terms of computational resources and time of execution, calculations are
not fully converged with respect to parameters such as k-points, empty bands or G-vectors.

SCF step (Quantum ESPRESSO)
----------------------------

Using the AiiDA quantumespresso.pw plugin, we begin with submitting an SCF calculation.
We are going to use the ``pk`` of the SCF calculation in the next steps.
We use the PwBaseWorkChain to submit a pw calculation, in such  a way to have automatic
error handling and restarting from failed runs.

For details on how to use the quantumespresso.pw plugin, please refer to the plugins documentation page. Remember to replace the codename
and pseudo-family with those configured in your AiiDA installation. NB: Yambo can be used only with norm-conserving pseudopotentials!


.. include:: ../../../../examples/plugin/scf_baseWorkchain.py
   :literal:

As you can notice, we use the "argparse" module to provide some inputs from the shell, like the code and the pseudos to be used in
the simulation. In practice, the command to be run would be like:

::

    verdi run name_of_the_script.py --code <pk of the pw code> --pseudo <name of the pseudofamily>

NSCF step (Quantum ESPRESSO) for G0W0
-------------------------------------
Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the GW calculation.

.. include:: ../../../../examples/plugin/nscf_baseWorkchain.py
   :literal:


P2Y step (Yambo)
-------------------------------------
Now we use the Yambo plugin to run the p2y code, converting the Quantum ESPRESSO files into a NetCDF Yambo database.

.. include:: ../../../../examples/plugin/yambo_p2y.py
   :literal:



G0W0 (Yambo)
------------
Now we are ready to run a G0W0 calculation in the plasmon-pole approximation (PPA), in particular we compute the direct band gap at Gamma of hBN.

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



To retrieve additional files:

::

    settings = ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01',
                        'aiida.out/ndb.QP','aiida.out/ndb.HF_and_locXC']})
    builder.use_settings(settings)

This selects the additional files that will  be retrieved and parsed after a calculation. Supported
files include the report files ``r-*``, text outputs ``o-*``, logs, the quasiparticle
database for GW calculations ``aiida.out/ndb.QP``, and the Hartree-Fock and local exchange
db ``aiida.out/ndb.HF_and_locXC``.
