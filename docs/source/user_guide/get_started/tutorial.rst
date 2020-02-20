.. _sec.yambo_calc_plugin:

.. _my-ref-to-yambo-tutorial:

Yambo-AiiDA  Tutorial
=====================

.. toctree::
   :maxdepth: 2

The following tutorial shows how to run a G0W0 calculation and how to compute an IP-RPA spectrum with Yambo for bulk hBN.
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

::

  #!/usr/bin/env runaiida
  # -*- coding: utf-8 -*-
  from __future__ import absolute_import
  from __future__ import print_function
  import sys
  import os
  from aiida.plugins import DataFactory
  from aiida.engine import submit
  from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
  from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
  from ase import Atoms

  ###### setting the machine options ######
  options = {
      'max_wallclock_seconds': 24* 60 * 60,
      'resources': {
          "num_machines": 1,
          "num_mpiprocs_per_machine":1,
  #        "num_cores_per_mpiproc":16//8,
      },
  #    'queue_name':'s3par',
      'environment_variables': {},
  #    'custom_scheduler_commands': u"#PBS -N hBN_gw \nexport OMP_NUM_THREADS=2",
      }

  metadata = {
      'options':options,
      'label': 'hBN -scf- workchain',
  }

  ###### setting the lattice structure ######

  alat = 2.4955987320 # Angstrom
  the_cell = [[1.000000*alat,   0.000000,   0.000000],
              [-0.500000*alat,  0.866025*alat,   0.000000],
              [0.000000,   0.000000,  6.4436359260]]

  atoms = Atoms('BNNB', [(1.2477994910, 0.7204172280, 0.0000000000),
  (-0.0000001250, 1.4408346720, 0.0000000000),
  (1.2477994910, 0.7204172280, 3.2218179630),
  (-0.0000001250,1.4408346720, 3.2218179630)],
  cell = [1,1,1])
  atoms.set_cell(the_cell, scale_atoms=False)
  atoms.set_pbc([True,True,True])

  StructureData = DataFactory('structure')
  structure = StructureData(ase=atoms)

  ###### setting the kpoints mesh ######

  KpointsData = DataFactory('array.kpoints')
  kpoints = KpointsData()
  kpoints.set_kpoints_mesh([6,6,2])

  ###### setting the scf parameters ######

  Dict = DataFactory('dict')
  params_scf = {
      'CONTROL': {
          'calculation': 'scf',
          'verbosity': 'high',
          'wf_collect': True
      },
      'SYSTEM': {
          'ecutwfc': 130.,
          'force_symmorphic': True,
          'nbnd': 20
      },
      'ELECTRONS': {
          'mixing_mode': 'plain',
          'mixing_beta': 0.7,
          'conv_thr': 1.e-8,
          'diago_thr_init': 5.0e-6,
          'diago_full_acc': True
      },
  }

  parameter_scf = Dict(dict=params_scf)


  ###### creation of the workchain ######

  builder = PwBaseWorkChain.get_builder()
  builder.pw.structure = structure
  builder.pw.parameters = parameter_scf
  builder.kpoints = kpoints
  builder.pw.metadata.options.max_wallclock_seconds = \
          options['max_wallclock_seconds']
  builder.pw.metadata.options.resources = \
          dict = options['resources']
  #builder.pw.metadata.options.queue_name = options['queue_name']
  #builder.pw.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']

  ###### inputs parameters, to be provided from shell ######

  if __name__ == "__main__":
      import argparse
      parser = argparse.ArgumentParser(description='SCF calculation.')
      parser.add_argument(
          '--code',
          type=int,
          dest='code_pk',
          required=True,
          help='The pw codename to use')

      parser.add_argument(
          '--pseudo',
          type=str,
          dest='pseudo_family',
          required=True,
          help='The pseudo family to use')
      args = parser.parse_args()
      builder.pw.code = load_node(args.code_pk)
      builder.pw.pseudos = validate_and_prepare_pseudos_inputs(
                  builder.pw.structure, pseudo_family = Str(args.pseudo_family))
      running = submit(builder)
      print("Submitted PwBaseWorkchain; with pk={}".format(running.pk))

As you can notice, we use the "argparse" module to provide some inputs from the shell, like the code and the pseudos to be used in
the simulation. In practice, the command to be run would be like:

::
    verdi run name_of_the_script.py --code <pk of the pw code> --pseudo <name of the pseudofamily>

NSCF step (Quantum ESPRESSO) for G0W0
-------------------------------------
Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the GW calculation.

::

  #!/usr/bin/env runaiida
  # -*- coding: utf-8 -*-
  from __future__ import absolute_import
  from __future__ import print_function
  import sys
  import os
  from aiida.plugins import DataFactory
  from aiida.engine import submit
  from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
  from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
  from ase import Atoms

  ###### setting the machine options ######
  options = {
      'max_wallclock_seconds': 24* 60 * 60,
      'resources': {
          "num_machines": 1,
          "num_mpiprocs_per_machine":1,
  #        "num_cores_per_mpiproc":2,
      },
  #    'queue_name':'s3par',
      'environment_variables': {},
  #    'custom_scheduler_commands': u"#PBS -N hBN_gw \nexport OMP_NUM_THREADS=2",
      }

  metadata = {
      'options':options,
      'label': 'hBN -scf- workchain',
  }

  ###### setting the lattice structure ######

  alat = 2.4955987320 # Angstrom
  the_cell = [[1.000000*alat,   0.000000,   0.000000],
              [-0.500000*alat,  0.866025*alat,   0.000000],
              [0.000000,   0.000000,  6.4436359260]]

  atoms = Atoms('BNNB', [(1.2477994910, 0.7204172280, 0.0000000000),
  (-0.0000001250, 1.4408346720, 0.0000000000),
  (1.2477994910, 0.7204172280, 3.2218179630),
  (-0.0000001250,1.4408346720, 3.2218179630)],
  cell = [1,1,1])
  atoms.set_cell(the_cell, scale_atoms=False)
  atoms.set_pbc([True,True,True])

  StructureData = DataFactory('structure')
  structure = StructureData(ase=atoms)

  ###### setting the kpoints mesh ######

  KpointsData = DataFactory('array.kpoints')
  kpoints = KpointsData()
  kpoints.set_kpoints_mesh([6,6,2])

  ###### setting the nscf parameters ######

  Dict = DataFactory('dict')
  params_scf = {
      'CONTROL': {
          'calculation': 'nscf',
          'verbosity': 'high',
          'wf_collect': True
      },
      'SYSTEM': {
          'ecutwfc': 130.,
          'force_symmorphic': True,
          'nbnd': 150
      },
      'ELECTRONS': {
          'mixing_mode': 'plain',
          'mixing_beta': 0.7,
          'conv_thr': 1.e-8,
          'diago_thr_init': 5.0e-6,
          'diago_full_acc': True
      },
  }

  parameter_scf = Dict(dict=params_scf)

  ###### creation of the workchain ######

  builder = PwBaseWorkChain.get_builder()
  builder.pw.structure = structure
  builder.pw.parameters = parameter_scf
  builder.kpoints = kpoints
  builder.pw.metadata.options.max_wallclock_seconds = \
          options['max_wallclock_seconds']
  builder.pw.metadata.options.resources = \
          dict = options['resources']
  #builder.pw.metadata.options.queue_name = options['queue_name']
  #builder.pw.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']

  ###### inputs parameters, to be provided from shell ######

  if __name__ == "__main__":
      import argparse
      parser = argparse.ArgumentParser(description='SCF calculation.')
      parser.add_argument(
          '--code',
          type=int,
          dest='code_pk',
          required=True,
          help='The pw codename to use')
      parser.add_argument(
          '--parent',
          type=int,
          dest='parent_pk',
          required=True,
          help='The parent to use')

      parser.add_argument(
          '--pseudo',
          type=str,
          dest='pseudo_family',
          required=True,
          help='The pseudo family to use')
      args = parser.parse_args()
      builder.pw.code = load_node(args.code_pk)
      builder.pw.pseudos = validate_and_prepare_pseudos_inputs(
                  builder.pw.structure, pseudo_family = Str(args.pseudo_family))
      builder.pw.parent_folder = load_node(args.parent_pk).outputs.remote_folder

      running = submit(builder)
      print("Submitted PwBaseWorkchain; with pk={}".format(running.pk))


P2Y step (Yambo)
-------------------------------------
Now we use the Yambo plugin to run the p2y code, converting the Quantum ESPRESSO files into a NetCDF Yambo database.

::

  #!/usr/bin/env runaiida
  # -*- coding: utf-8 -*-
  from __future__ import absolute_import
  from __future__ import print_function
  import sys
  import os
  from aiida.plugins import DataFactory, CalculationFactory
  from aiida.orm import List, Dict
  from aiida.engine import submit
  from aiida_yambo.calculations.gw import YamboCalculation


  options = {
      'max_wallclock_seconds': 24*60*60,
      'resources': {
          "num_machines": 1,
          "num_mpiprocs_per_machine":1,
          "num_cores_per_mpiproc":1,
      },
  #    'queue_name':'s3par',
      'environment_variables': {},
  #    'custom_scheduler_commands': u"#PBS -N example_gw \nexport OMP_NUM_THREADS=1",
      }

  metadata = {
      'options':options,
      'label': 'example_gw',
  }

  builder = YamboCalculation.get_builder()
  builder.metadata.options.max_wallclock_seconds = \
          options['max_wallclock_seconds']
  builder.metadata.options.resources = \
          dict = options['resources']
  #builder.metadata.options.queue_name = options['queue_name']
  #builder.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']
  builder.precode_parameters = Dict(dict={})
  builder.settings = Dict(dict={'INITIALISE': False})

  if __name__ == "__main__":
      import argparse
      parser = argparse.ArgumentParser(description='YAMBO calculation.')
      parser.add_argument(
          '--code',
          type=int,
          dest='code_pk',
          required=True,
          help='The yambo(main code) codename to use')
      parser.add_argument(
          '--parent',
          type=int,
          dest='parent_pk',
          required=True,
          help='The parent to use')
      parser.add_argument(
          '--precode',
          type=int,
          dest='precode_pk',
          required=False,
          help='The precode to use')

      args = parser.parse_args()
      builder.preprocessing_code = load_node(args.precode_pk)
      builder.code = load_node(args.code_pk)
      builder.parent_folder = load_node(args.parent_pk).outputs.remote_folder
      running = submit(builder)
      print("Created p2y calculation; with pk={}".format(running.pk))



G0W0 (Yambo)
------------
Now we are ready to run a G0W0 calculation in the plasmon-pole approximation (PPA), in particular we compute the direct band gap at Gamma of hBN.

::

  #!/usr/bin/env runaiida
  # -*- coding: utf-8 -*-
  from __future__ import absolute_import
  from __future__ import print_function
  import sys
  import os
  from aiida.plugins import DataFactory, CalculationFactory
  from aiida.orm import List, Dict
  from aiida.engine import submit
  from aiida_yambo.calculations.gw import YamboCalculation

  options = {
      'max_wallclock_seconds': 24*60*60,
      'resources': {
          "num_machines": 1,
          "num_mpiprocs_per_machine":1,
          "num_cores_per_mpiproc":1,
      },
  #    'queue_name':'s3par',
      'environment_variables': {},
  #    'custom_scheduler_commands': u"#PBS -N example_gw \nexport OMP_NUM_THREADS=1",
      }

  metadata = {
      'options':options,
      'label': 'example_gw',
  }

  params_gw = {
          'ppa': True,
          'gw0': True,
          'HF_and_locXC': True,
          'em1d': True,
          'Chimod': 'hartree',
          #'EXXRLvcs': 40,
          #'EXXRLvcs_units': 'Ry',
          'BndsRnXp': [1, 10],
          'NGsBlkXp': 2,
          'NGsBlkXp_units': 'Ry',
          'GbndRnge': [1, 10],
          'DysSolver': "n",
          'QPkrange': [[1, 1, 8, 9]],
          'X_all_q_CPU': "1 1 1 1",
          'X_all_q_ROLEs': "q k c v",
          'SE_CPU': "1 1 1",
          'SE_ROLEs': "q qp b",
      }
  params_gw = Dict(dict=params_gw)


  builder = YamboCalculation.get_builder()
  builder.metadata.options.max_wallclock_seconds = \
          options['max_wallclock_seconds']
  builder.metadata.options.resources = \
          dict = options['resources']
  #builder.metadata.options.queue_name = options['queue_name']
  #builder.metadata.options.custom_scheduler_commands = options['custom_scheduler_commands']
  builder.parameters = params_gw
  builder.precode_parameters = Dict(dict={})
  builder.settings = Dict(dict={'INITIALISE': False, 'PARENT_DB': False})

  if __name__ == "__main__":
      import argparse
      parser = argparse.ArgumentParser(description='YAMBO calculation.')
      parser.add_argument(
          '--code',
          type=int,
          dest='code_pk',
          required=True,
          help='The yambo(main code) codename to use')
      parser.add_argument(
          '--parent',
          type=int,
          dest='parent_pk',
          required=True,
          help='The parent to use')
      parser.add_argument(
          '--precode',
          type=int,
          dest='precode_pk',
          required=False,
          help='The precode to use')

      args = parser.parse_args()
      builder.preprocessing_code = load_node(args.precode_pk)
      builder.code = load_node(args.code_pk)
      builder.parent_folder = load_node(args.parent_pk).outputs.remote_folder
      running = submit(builder)
      print("Created calculation; with pk={}".format(running.pk))

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
