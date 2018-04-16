.. _sec.yambo_calc_plugin: 

.. _my-ref-to-yambo-tutorial:

Yambo-AiiDA  Tutorial
=====================

.. toctree::
   :maxdepth: 2
   
The following tutorial shows how to run a G0W0 calculation and how to compute an IP-RPA spectrum with Yambo for bulk GaAs. In order to keep the tutorial light in terms of computational resources and time of execution, calculations are not fully converged with respect to parameters such as k-points, empty bands or G-vectors.

SCF step (Quantum ESPRESSO)
----------------------------

Using the AiiDA quantumespresso.pw plugin, we begin with submitting an SCF calculation. We are going to use the ``pk`` of the SCF calculation in the next steps.

For details on how to use the quantumespresso.pw plugin, please refer to the plugins documentation page. Remember to replace the codename
and pseudo-family with those configured in your AiiDA installation. NB: Yambo can be used only with norm-conserving pseudopotentials!

::
    
	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure


	StructureData = DataFactory('structure')

	a = 5.367 * pymatgen.core.units.bohr_to_ang
	structure_pmg = pymatgen.Structure(
		    lattice=[[-a, 0, a], [0, a, a], [-a, a, 0]],
		    species=['Ga', 'As'],
		    coords=[[0] * 3, [0.25] * 3]
		)
	structure = StructureData()
	structure.set_pymatgen_structure(structure_pmg)

	 
	ParameterData = DataFactory('parameter')
	    
	parameters = ParameterData(dict={
		      'CONTROL': {
		          'calculation': 'scf',
		          'restart_mode': 'from_scratch',
		          'wf_collect': True,
		          'verbosity' :'high',
		          },
		      'SYSTEM': {
		          'ecutwfc': 80.,
		          },
		      'ELECTRONS': {
		          'conv_thr': 1.e-10,
		          }})

	KpointsData = DataFactory('array.kpoints')
	kpoints = KpointsData() 
	kpoints.set_kpoints_mesh([8,8,8])
	    
	inputs = {}
	inputs['structure'] = structure
	inputs['kpoints'] = kpoints
	inputs['parameters'] = parameters
	inputs['_options'] = {'max_wallclock_seconds':30*60, 
		              'resources':{
		                          "num_machines": 1,
		                          #"num_mpiprocs_per_machine":1
		                           },
		               #'custom_scheduler_commands':u"your scheduler commands",
		                          }

	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='SCF calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The pw codename to use')
	   
	    parser.add_argument('--pseudo', type=str, dest='pseudo', required=True,
		                help='The pseudo family to use') 
	    args = parser.parse_args()
	    code = Code.get_from_string(args.codename)
	    inputs['code'] = code
	    inputs['pseudo'] = get_pseudos_from_structure(structure, args.pseudo )
	    process = PwCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)


NSCF step (Quantum ESPRESSO) for G0W0
-------------------------------------
Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the GW calculation. GW calculations often require several empty states and few k-points (at least in 3D), so we are going to use a different NSCF to compute the IP-RPA spectrum for which more k-points and less empty bands are needed.


::

	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure

	 
	ParameterData = DataFactory('parameter')
	    
	parameters = ParameterData(dict={
		      'CONTROL': {
		          'calculation': 'nscf',
		          'restart_mode': 'from_scratch',
		          'wf_collect': True,
		          'verbosity' :'high',
		          },
		      'SYSTEM': {
		          'ecutwfc': 80.,
		          'nbnd':50,
		          'force_symmorphic':True,
		          },
		      'ELECTRONS': {
		          'conv_thr': 1.e-10,
		          'diago_full_acc': True,
		          'diagonalization':'cg',
		          }})

	KpointsData = DataFactory('array.kpoints')
	kpoints = KpointsData() 
	kpoints.set_kpoints_mesh([6,6,6])
	    
	inputs = {}
	inputs['kpoints'] = kpoints
	inputs['parameters'] = parameters
	inputs['_options'] = {'max_wallclock_seconds':30*60, 
		              'resources':{
		                          "num_machines": 1,
		                          "num_mpiprocs_per_machine":1,
		                          },
		                       'custom_scheduler_commands': u"#SBATCH --account=Pra15_3963 \n" + 
		                       "#SBATCH --partition=knl_usr_dbg \n" +
		                       "#SBATCH --mem=86000 \n" +         "\n"+"\nexport OMP_NUM_THREADS=1\nexport MKL_NUM_THREADS=1"}
		                          
	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='NSCF calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The pw codename to use')
	    parser.add_argument('--pseudo', type=str, dest='pseudo', required=True,
		                help='The pseudo family to use')
	    parser.add_argument('--parent', type=int, dest='parent', required=True,
		                help='The parent  to use')
	    args = parser.parse_args()
	    code = Code.get_from_string(args.codename)
	    structure = load_node(args.parent).inp.structure
	    inputs['structure'] = structure
	    inputs['pseudo'] = get_pseudos_from_structure(structure, args.pseudo )
	    inputs['code'] = code
	    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
	    process = PwCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)

P2Y step (Yambo)
-------------------------------------
Now we use the Yambo plugin to run the p2y code, converting the Quantum ESPRESSO files into a NetCDF Yambo database.

::

	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure


	ParameterData = DataFactory('parameter')
	    
	inputs = {}
	inputs['settings'] = ParameterData(dict={'initialise': True})
	inputs['_options'] = {
		              'max_wallclock_seconds':30*60, 
		              'resources':{
		                          "num_machines": 1,
		                          "num_mpiprocs_per_machine":1,
		                          },
		               'custom_scheduler_commands':u"***",
		               }

	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='p2y calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The yambo code to use')
	    parser.add_argument('--precode', type=str, dest='precodename', required=True,
		                help='The yambo precodename to use')
	    parser.add_argument('--parent', type=int, dest='parent', required=True,
		                help='The parent to use')
	    args = parser.parse_args()
	    precode = Code.get_from_string(args.precodename)
	    code = Code.get_from_string(args.codename)
	    inputs['preprocessing_code'] = precode
	    inputs['code'] = code
	    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
	    process = YamboCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)



G0W0 (Yambo)
------------
Now we are ready to run a G0W0 calculation in the plasmon-pole approximation (PPA), in particular we compute the direct band gap at Gamma of GaAs.

::

	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure

	 
	ParameterData = DataFactory('parameter')
	    
	parameters = ParameterData(dict={'ppa': True,
		                         'gw0': True,
		                         'HF_and_locXC': True,
		                         'em1d': True,
		                         'Chimod':'hartree',
		                         'FFTGvecs': 50,
		                         'FFTGvecs_units': 'Ry',
		                         'BndsRnXp': (1,50),
		                         'NGsBlkXp': 2,
		                         'NGsBlkXp_units': 'Ry',
		                         'GbndRnge': (1,50),
		                         'DysSolver': "n",
		                         'QPkrange': [(1,1,9,10)],
		                         'X_all_q_CPU': "1 1 1 1",
		                         'X_all_q_ROLEs': "q k c v",
		                         'SE_CPU': "1 1 1",
		                         'SE_ROLEs': "q qp b",
		                        })

	inputs = {}
	inputs['parameters'] = parameters
	inputs['_options'] = {'max_wallclock_seconds':30*60, 
		              'resources':{
		                          "num_machines": 1,
		                          "num_mpiprocs_per_machine":1,
		                          },
		                       'custom_scheduler_commands': u"***"}
		                          
		                          

	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='YAMBO calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The pw codename to use')
	    parser.add_argument('--parent', type=int, dest='parent', required=True,
		                help='The parent  to use')
	    args = parser.parse_args()
	    code = Code.get_from_string(args.codename)
	    inputs['code'] = code
	    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
	    process = YamboCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)

The quasiparticle corrections and the renormalization factors can be accessed from the Yambo calculation (yambo_calc) using the output bands and array data:

::

	yambo_calc = load_node(pk)
	energies_DFT = yambo_calc.out.array_qp.get_array('E_0')
	QP_corrections =  yambo_calc.out.array_qp.get_array('E_minus_Eo')
	Z_factors =  yambo_calc.out.array_qp.get_array('Z')
	kpoint_band_array = yambo_calc.out.array_qp.get_array('qp_table')
	kpoints = y.out.bands_quasiparticle.get_kpoints()



NSCF step (Quantum ESPRESSO) for IP-RPA spectrum
------------------------------------------------
Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the IP-RPA calculation. 

::

	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure

	 
	ParameterData = DataFactory('parameter')
	    
	parameters = ParameterData(dict={
		      'CONTROL': {
		          'calculation': 'nscf',
		          'restart_mode': 'from_scratch',
		          'wf_collect': True,
		          'verbosity' :'high',
		          },
		      'SYSTEM': {
		          'ecutwfc': 80.,
		          'nbnd':20,
		          'force_symmorphic':True,
		          },
		      'ELECTRONS': {
		          'conv_thr': 1.e-10,
		          'diago_full_acc': True,
		          'diagonalization':'cg',
		          }})

	KpointsData = DataFactory('array.kpoints')
	kpoints = KpointsData() 
	kpoints.set_kpoints_mesh([16,16,16])
	    
	inputs = {}
	inputs['kpoints'] = kpoints
	inputs['parameters'] = parameters
	inputs['_options'] = {'max_wallclock_seconds':30*60, 
		              'resources':{
		                          "num_machines": 1,
		                          "num_mpiprocs_per_machine":64,
		                           },
		                       'custom_scheduler_commands': u"#SBATCH --account=Pra15_3963 \n" + 
		                       "#SBATCH --partition=knl_usr_dbg \n" +
		                       "#SBATCH --mem=86000 \n" +         "\n"+"\nexport OMP_NUM_THREADS=1\nexport MKL_NUM_THREADS=1"}
		                          
	num_pools = 8
	inputs['settings'] = ParameterData(dict={'cmdline':['-nk',str(num_pools)]})

	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='NSCF calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The pw codename to use')
	    parser.add_argument('--pseudo', type=str, dest='pseudo', required=True,
		                help='The pseudo family to use')
	    parser.add_argument('--parent', type=int, dest='parent', required=True,
		                help='The parent  to use')
	    args = parser.parse_args()
	    code = Code.get_from_string(args.codename)
	    structure = load_node(args.parent).inp.structure
	    inputs['structure'] = structure
	    inputs['pseudo'] = get_pseudos_from_structure(structure, args.pseudo )
	    inputs['code'] = code
	    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
	    process = PwCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)

Absorption spectrum IP-RPA (Yambo)
----------------------------------

We compute the IP-RPA spectrum using Yambo. In order to include local fields effect you can replace 'Chimod': "IP" with 'Chimod': "Hartree" and add a value for 'NGsBlkXd'. 


::

	#!/usr/bin/env runaiida
	# -*- coding: utf-8 -*-
	import sys
	import os
	from aiida.orm import DataFactory, CalculationFactory
	from aiida.common.example_helpers import test_and_get_code
	from aiida.orm.data.base import List
	from aiida.orm import Code
	from aiida.orm import DataFactory
	import pymatgen
	from aiida.work.run import submit
	from aiida_yambo.calculations.gw import YamboCalculation
	from aiida_quantumespresso.calculations.pw import PwCalculation
	from aiida.orm.data.upf import UpfData, get_pseudos_from_structure

	 
	ParameterData = DataFactory('parameter')
	    
	parameters = ParameterData(dict={
		             'optics': True,
		             'chi': True,
		             'Chimod': "IP",
		             'QpntsRXd': (1.,1.),
		             'BndsrnXd': (1.,20.),
                             'FFTGvecs': 50,
                             'FFTGvecs_units': 'Ry',
		            # 'NGsBlkXd': 1,              #For Hartree
		            # 'NGsBlkXd_units': 'RL',      
		             'EnRngeXd': (0.00,10.),
		             'EnRngeXd_units': 'eV',
		             'DmRngeXd': (0.15,0.3),
		             'DmRngeXd_units': 'eV',
		             'ETStpsXd': 1000,
		             'LongDrXd': (1.,0.0,0.0),
		             'X_all_q_CPU': "1 1 1 1",
		             'X_all_q_ROLEs': "q k c v",
		            })

	inputs = {}
	inputs['parameters'] = parameters
	inputs['_options'] = {'max_wallclock_seconds':30*60,
		              'resources':{
		                          "num_machines": 1,
		                          "num_mpiprocs_per_machine":1,
		                          },
		                     'custom_scheduler_commands': u"***" }   
	if __name__ == "__main__":
	    import argparse
	    parser = argparse.ArgumentParser(description='YAMBO calculation.')
	    parser.add_argument('--code', type=str, dest='codename', required=True,
		                help='The pw codename to use')
	    parser.add_argument('--parent', type=int, dest='parent', required=True,
		                help='The parent  to use')
	    args = parser.parse_args()
	    code = Code.get_from_string(args.codename)
	    inputs['code'] = code
	    inputs['parent_folder'] = load_node(args.parent).out.remote_folder
	    process = YamboCalculation.process()
	    running = submit(process, **inputs)
	    print "Created calculation; with pid={}".format(running.pid)


The real and imaginary part of the dielectric function can be accessed from the Yambo calculation (yambo_calc) using the output array:

::

	yambo_calc = load_node(pk)
	energies = yambo_calc.out.array_eps.get_array('E_ev')
	eps_re =  yambo_calc.out.array_eps.get_array('EPS_Re')
	eps_im =  yambo_calc.out.array_eps.get_array('EPS_Im')

the spectrum can be directly be plotted with matplotlib:

:: 

	import matplotlib.pyplot as plt
	plt.plot(energies,eps_im)
	plt.show()


To retrieve additional files:

::

    settings = ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01',
                        'aiida/ndb.QP','aiida/ndb.HF_and_locXC']})
    calc.use_settings(settings)

This selects theadditional files that will  be retreived and parsed after a calculation. Supported
files include the report files ``r-*``, text outputs ``o-*``, logs, the quasiparticle 
database for GW calculations ``aiida/ndb.QP``, and the Hartree Fock and local exchange
db ``aiida/ndb.HF_and_locXC``. 



