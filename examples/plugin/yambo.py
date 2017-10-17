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
                                 'BndsRnXp':[1,50],
                                 'EXXRLvcs': 10,
                                 'EXXRLvcs_units': 'Ry',
                                 'BndsRnXp': (1,50),
                                 'NGsBlkXp': 2,
                                 'NGsBlkXp_units': 'Ry',
                                 'GbndRnge': (1,50),
                                 'DysSolver': "n",
                                 'QPkrange': [(1,1,4,4),(1,1,5,5),(2,2,4,4),(2,2,5,5)],
                                 'X_all_q_CPU': "1 1 16 4",
                                 'X_all_q_ROLEs': "q k c v",
                                 'SE_CPU': "1 4 16",
                                 'SE_ROLEs': "q qp b",
                                })

inputs = {}
inputs['parameters'] = parameters
inputs['_options'] = {'max_wallclock_seconds':30*60, 
                      'resources':{
                                  "num_machines": 1,
                                  "num_mpiprocs_per_machine":64,
                                  },
                      'custom_scheduler_commands':u"#PBS -A Pra15_3963
                                                    \nexport OMP_NUM_THREADS=64
                                                    \nexport MKL_NUM_THREADS=64",
                      }

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
    process = PwCalculation.process()
    running = submit(process, **inputs)
    print "Created calculation; with pid={}".format(running.pid)

