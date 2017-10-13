#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
import os

__copyright__ = u"Copyright (c), 2014-2015, École Polytechnique Fédérale de Lausanne (EPFL), Switzerland, Laboratory of Theory and Simulation of Materials (THEOS). All rights reserved."
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file"
__version__ = "0.4.1"

UpfData = DataFactory('upf')
ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
KpointsData = DataFactory('array.kpoints')
YamboCalc = CalculationFactory('yambo') 
QepwCalc = CalculationFactory('quantumespresso.pw') 

send = True
parent_id = 15296 # QE calculation
codename = 'yambo@theospc15'
precodename = 'p2y@theospc15'

queue = None
#####

code = Code.get_from_string(codename)
pre_code = Code.get_from_string(precodename)

######
parameters = ParameterData(dict={'optics': True,
                                 'chi': True,
                                 'QpntsRXd': (1.,1.),
                                 'BndsrnXd': (1.,30.), 
                                 'EnRngeXd': (0.5,3.5),
                                 'EnRngeXd_units': 'eV',
                                 'DmRngeXd': (0.1,0.3),
                                 'DmRngeXd_units': 'eV',
                                 'ETStpsXd': 300,
                                 'LongDrXd': (1.,0.,0.),
                                 'Chimod': "IP",
                                 #'FFTGvecs': 500,
                                 #'FFTGvecs_units': 'RL',
                                 #'LongDrXp': (1.,1.,1.),
                                 #'LongDrXp_units': 'eV',
                                 }
                           )
precode_parameters = ParameterData(dict={})
                                           
settings=None

parentcalc = QepwCalc.get_subclass_from_pk(parent_id)

calc = code.new_calc()
calc.set_max_wallclock_seconds(30*60) # 30 min
calc.set_resources({"num_machines": 1,'num_mpiprocs_per_machine':8})
if queue is not None:
    calc.set_queue_name(queue)
calc.use_parameters(parameters)
calc.use_parent_calculation(parentcalc)
calc.use_preprocessing_code(pre_code)
calc.use_precode_parameters(precode_parameters)

# optional
if settings is not None:
    calc.use_settings(settings)

if not send:
    subfolder, script_filename = calc.submit_test()
    print "Test_submit for calculation (uuid='{}')".format(
        calc.uuid)
    print "Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
        ))
else:
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid,calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid,calc.dbnode.pk)
