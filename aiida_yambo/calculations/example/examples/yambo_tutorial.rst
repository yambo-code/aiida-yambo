.. _my-ref-to-yambo-tutorial:

Yambo G0W0 Tutorial
====================

.. toctree::
   :maxdepth: 2
   
The following shows how to run a single G0W0 calculation with ``yambo``, using an installation of AiiDA with a computer
already setup,  ``pw.x`` and ``yambo`` codes configured.
There will be three separate jobs submited as AiiDA calculations, one for the PWscf  `scf`, one for the corresponding `nscf`,
and finally the actual `yambo` calculation. 

PWscf `scf` step
-----------------

Using the AiiDA PWscf plugin submit the following calculation and note its `pk` which will be required for subsequent steps.
For details on how to use the PWscf plugin, please refer to the plugins documentation page. Remember to replace the codename
and Pseudo family with one configured in your AiiDA installation.

::
    
    from aiida import load_dbenv, is_dbenv_loaded
    if not is_dbenv_loaded():
        load_dbenv()
    
    codename = 'codename@machine'
    from aiida.orm import Code
    code = Code.get_from_string(codename)
    from aiida.orm import DataFactory
    StructureData = DataFactory('structure')
    cell=[[   15.8753100000,    0.0000000000,    0.0000000000],
        [0.0000000000 , 15.8753100000 , 0.0000000000],
        [0.0000000000  , 0.0000000000  , 2.4696584760]]
    
    s = StructureData(cell=cell)
    s.append_atom(position=(0.0000000000, 0.0000000000, -0.5857830640), symbols='C')
    s.append_atom(position=(0.6483409550, 0.0000000000, 0.5857863990), symbols='C')
    s.append_atom(position=(-1.0769905460, 0.0000000000, -0.5902956470), symbols='H')
    s.append_atom(position=(1.7253315010, 0.0000000000, 0.5902989820), symbols='H')
    
    s.store()
    
    ParameterData = DataFactory('parameter')
    
    parameters = ParameterData(dict={
              'CONTROL': {
                  'calculation': 'scf',
                  'restart_mode': 'from_scratch',
                  'wf_collect': True,
                  'verbosity' :'high',
                  },
              'SYSTEM': {
                  'ecutwfc': 45.,
                  },
              'ELECTRONS': {
                  'conv_thr': 1.e-8,
                  'electron_maxstep ': 50,
                  'mixing_mode': 'plain',
                  'mixing_beta' : 0.4
                  }})
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData() 
    kpoints.set_kpoints_mesh([1,1,30])
    calc = code.new_calc()
    calc.set_max_wallclock_seconds(120*60) # 120 min
    calc.set_resources({"num_machines": 4,"num_mpiprocs_per_machine":16,"num_cores_per_machine":32 })
    
    calc.use_structure(s)
    calc.use_code(code)
    calc.use_parameters(parameters)
    calc.use_kpoints(kpoints)
    
    calc.use_pseudos_from_family('YourPseudoFamily')
    calc.label = "Scf test for CH"
    calc.store_all()
    print "created calculation; with uuid='{}' and PK={}".format(calc.uuid,calc.pk)
    calc.submit()

PWscf `nscf` step
-----------------
Using the ``pk`` of the preceeding ``scf`` calculation, run a ``nscf`` with PWscf, refer to the
PWscf plugin for more information. Replace the ``pk`` in this example with the ``pk`` from your 
``scf`` calculation.

::
    
    from aiida import load_dbenv, is_dbenv_loaded
    if not is_dbenv_loaded():
        load_dbenv()
    
    codename = 'codename@machine'
    from aiida.orm import Code
    code = Code.get_from_string(codename)
    from aiida.orm import DataFactory
    ParameterData = DataFactory('parameter')
    parameters = ParameterData(dict={
              'CONTROL': {
                  'calculation': 'nscf',
                  'restart_mode': 'from_scratch',
                  'wf_collect': True,
                  'verbosity' :'high',
                  },
              'SYSTEM': {
                  'ecutwfc': 45,
                  'force_symmorphic': True,
                  'nbnd':  50
                  },
              'ELECTRONS': {
                  'conv_thr': 1.e-8,
                  'electron_maxstep ': 50,
                  'mixing_mode': 'plain',
                  'mixing_beta' : 0.4
                  }})
    
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([1,1,30])
    
    parentcalc = load_node(219) # replace 219 with your scf pk
    s = parentcalc.inp.structure
    parent_folder = parentcalc.out.remote_folder
    
    calc = code.new_calc()
    calc.use_parent_folder(parent_folder)
    calc.set_max_wallclock_seconds(80*60) # 80 min
    calc.set_resources({"num_machines": 4,"num_mpiprocs_per_machine":16,"num_cores_per_machine":32 })
    
    calc.use_structure(s)
    calc.use_code(code)
    calc.use_parameters(parameters)
    calc.use_kpoints(kpoints)
    
    calc.use_pseudos_from_family('YourPseudoFamily')
    calc.label = "nScf  for  rutile tio2"
    calc.store_all()
    print "created calculation; with uuid='{}' and PK={}".format(calc.uuid,calc.pk)
    calc.submit()


Yambo Run
---------
Yambo requires preprocessing PWscf output before it can be run, and this is done using the
``p2y`` executable. This will be done normally before ``yambo setup`` and the ``yambo`` 
calculation. To configure AiiDA to do these steps, use the Yambo plugin as follows:

::

    codename = 'yambo_codename@machine'
    precodename = 'p2y_codename@machine'
    code = Code.get_from_string(codename)
    pre_code = Code.get_from_string(precodename)
    calc = code.new_calc()
    calc.use_preprocessing_code(pre_code)

This configures AiiDA to run the  ``p2y`` binary first, as well as the initialization step of yambo.

After AiiDA has performed the required precursor steps, we need to run ``yambo`` with the correct
parameters to perform  a G0W0  calculation 

Parameters
----------
The parameters passed to ``yambo`` are provided as a  python dictionary, wrapped by the AiiDA 
ParameterData data structure. Yambo input options that can accept multi-line parameters use 
a list of python tuples, those that take integers and strings are setup as python strings and
integers: 

::

    parameters = ParameterData(dict={'ppa': True,
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
                                 'SE_ROLEs': "q qp b",
                                 'SE_Threads':  1,
                                 'RandQpts': 0,
                                 'RandGvec': 1,
                                 'RandGvec_units': 'RL',
                                 'CUTGeo': "none",
                                 'CUTBox': (0.0,0.0,0.0),
                                 'CUTRadius': 0.0,
                                 'CUTCylLen': 0.0,
                                 'EXXRLvcs': 170943,
                                 'EXXRLvcs_units': 'RL',
                                 'BndsRnXp': (1,50),
                                 'NGsBlkXp': 3,
                                 'NGsBlkXp_units': 'Ry',
                                 'LongDrXp': (1,0,0),
                                 'PPAPntXp': 20,
                                 'PPAPntXp_units': 'eV',
                                 'GbndRnge': (1,50),
                                 'GDamping': 0.1,
                                 'GDamping_units': 'eV',
                                 'dScStep': 0.1,
                                 'dScStep_units': 'eV',
                                 'GTermKind': "none",
                                 'DysSolver': "n",
                                  "Chimod": "",
                                 'QPkrange': [(1,1,5,6),(16,16,5,6)],
                                 }
                           )
    calc.use_parameters(parameters)

For the results to be retrieved and parsed, this plugin accepts a list of
files to retreive in a settings dictionary:

::

    settings = ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01',
                        'aiida/ndb.QP','aiida/ndb.HF_and_locXC']})
    calc.use_settings(settings)

This selects the files that will  be retreived and parsed after a calculation. Supported
files include the report files ``r-*``, text outputs ``o-*``, logs, the quasiparticle 
database for GW calculations ``aiida/ndb.QP``, and the Hartree Fock and local exchange
db ``aiida/ndb.HF_and_locXC``. 

To ensure that the ``yambo`` calculation is run in the output folder from the preceeding
PWscf ``nscf`` calculation, we need to provide it to the Yambo plugin as follows:

::

    parentcalc = QepwCalc.get_subclass_from_pk(225) #  == nscf calc
    calc.use_parent_calculation(parentcalc)
    calc.use_preprocessing_code(pre_code)

Replacing the ``pk`` with that of your ``nscf`` calculation. With this done, we can store the
calculation and run it.

::

    calc.store_all()
    print "created calculation; with uuid='{}' and PK={}".format(calc.uuid,calc.pk)
    calc.submit()



Complete Yambo input example:
------------------------------
Here is the complete script for the ``yambo``  calculation described above:

::

    from aiida import load_dbenv, is_dbenv_loaded
    if not is_dbenv_loaded():
        load_dbenv()
    
    UpfData = DataFactory('upf')
    ParameterData = DataFactory('parameter')
    StructureData = DataFactory('structure')
    RemoteData = DataFactory('remote')
    KpointsData = DataFactory('array.kpoints')
    QepwCalc = CalculationFactory('quantumespresso.pw')
    YamboCalc = CalculationFactory('yambo')
    
    codename = 'yambo_marconi@marconi'
    precodename = 'p2y_marconi@marconi'
    code = Code.get_from_string(codename)
    pre_code = Code.get_from_string(precodename)
    
    ######
    parameters = ParameterData(dict={'ppa': True,
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
                                     'SE_ROLEs': "q qp b",
                                     'SE_Threads':  1,
                                     'RandQpts': 0,
                                     'RandGvec': 1,
                                     'RandGvec_units': 'RL',
                                     'CUTGeo': "none",
                                     'CUTBox': (0.0,0.0,0.0),
                                     'CUTRadius': 0.0,
                                     'CUTCylLen': 0.0,
                                     'EXXRLvcs': 170943,
                                     'EXXRLvcs_units': 'RL',
                                     'BndsRnXp': (1,50),
                                     'NGsBlkXp': 3,
                                     'NGsBlkXp_units': 'Ry',
                                     'LongDrXp': (1,0,0),
                                     'PPAPntXp': 20,
                                     'PPAPntXp_units': 'eV',
                                     'GbndRnge': (1,50),
                                     'GDamping': 0.1,
                                     'GDamping_units': 'eV',
                                     'dScStep': 0.1,
                                     'dScStep_units': 'eV',
                                     'GTermKind': "none",
                                     'DysSolver': "n",
                                      "Chimod": "",
                                     'QPkrange': [(1,1,5,6),(16,16,5,6)],
                                     }
                               )
    precode_parameters = ParameterData(dict={})
    settings = ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":['r-*','o-*','LOG/l-*01']})
    calc = code.new_calc()
    calc.set_max_wallclock_seconds(240*60) # 4 hr
    calc.set_max_memory_kb(1*128*1000000) # 128 GB 
    calc.set_resources({"num_machines": 8,"num_mpiprocs_per_machine":16,"num_cores_per_machine":32 })
    calc.set_custom_scheduler_commands("#PBS -A  Pra12_3100_0")
    
    parentcalc = QepwCalc.get_subclass_from_pk(225) # 23 == nscf calc

    calc.use_parent_calculation(parentcalc)
    calc.use_preprocessing_code(pre_code)
    calc.use_precode_parameters(precode_parameters)
    calc.use_parameters(parameters)
    calc.use_settings(settings)
    
    calc.label = "Yambo GW test"
    calc.description = "Yambo first testrun calculation "
    calc.store_all()
    print "created calculation; with uuid='{}' and PK={}".format(calc.uuid,calc.pk)
    calc.submit()

