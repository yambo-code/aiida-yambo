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


codename = 'pw_6.1@fidis' #'pw_6.2_2Dcode@marconi_knl' 


code = Code.get_from_string(codename)

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
                  'ecutwfc': 20.,
                  },
              'ELECTRONS': {
                  'conv_thr': 1.e-8,
                  'electron_maxstep ': 50,
                  'mixing_mode': 'plain',
                  'mixing_beta' : 0.7,
                  }})

KpointsData = DataFactory('array.kpoints')
kpoints = KpointsData() 
kpoints.set_kpoints_mesh([4,4,4])
    
inputs = {}
inputs['code'] = code
inputs['structure'] = structure
inputs['kpoints'] = kpoints
inputs['parameters'] = parameters
inputs['pseudo'] = get_pseudos_from_structure(structure, 'SSSP_efficiency_v0.95' )
#inputs['pseudos_from_family'] = 'SSSP_efficiency_v0.95' 
inputs['_options'] = {'max_wallclock_seconds':30*60, 
                      'resources':{
                                  "num_machines": 1,
                                  "num_mpiprocs_per_machine":28,
                                  }}
process = PwCalculation.process()
running = submit(process, **inputs)  
print "Created calculation; with pid={}".format(running.pid)

