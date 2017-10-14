#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
import sys
import os

__copyright__ = u"Copyright (c), This file is part of the AiiDA platform. For further information please visit http://www.aiida.net/.. All rights reserved."
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.6.0"
__authors__ = "The AiiDA team."

# test pw restart:
# do first a pw calculation (e.g. ./test_pw.py --send pw_codename, or 
# ./test_pw_vcrelax.py --send pw_codename)
# then use a this one with the previous pw calculation as parent
# (no need to specify codename):
# ./test_pw_restart --send pw_parent_calc_pk

# NOTE: if calculation was vc-relax, restart works only if wf_collect was
# set to False ...


################################################################
UpfData = DataFactory('upf')
ParameterData = DataFactory('parameter')
StructureData = DataFactory('structure')
RemoteData = DataFactory('remote')
KpointsData = DataFactory('array.kpoints')

# Used to test the parent calculation
QepwCalc = CalculationFactory('quantumespresso.pw')

try:
    dontsend = sys.argv[1]
    if dontsend == "--dont-send":
        submit_test = True
    elif dontsend == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print >> sys.stderr, ("The first parameter can only be either "
                          "--send or --dont-send")
    sys.exit(1)

try:
    parent_id = sys.argv[2]
except IndexError:
    print >> sys.stderr, ("Must provide as second parameter the parent ID")
    sys.exit(1)


#####
# test parent

try:
    int(parent_id)
except ValueError:
    raise ValueError('Parent_id not an integer: {}'.format(parent_id))


try:
    pseudo_family = sys.argv[3]
except IndexError:
    print >> sys.stderr, "Error, pseudo_family not found"
    sys.exit(1)


queue = None
# queue = "P_share_queue"

#####
settings = ParameterData(dict={})

parameters = ParameterData(dict={
    'CONTROL': {
        'calculation': 'nscf',
        'restart_mode': 'from_scratch',
        'wf_collect': True,
        'tstress': True,
        'tprnfor': True,
    },
    'SYSTEM': {
        'ecutwfc': 40.,
        'ecutrho': 320.,
        'force_symmorphic': True,
        'nbnd': 30,
    },
    'ELECTRONS': {
        'conv_thr': 1.e-10,
        'diago_full_acc': True,
    }})

kpoints = KpointsData()
kpoints_mesh = 2
kpoints.set_kpoints_mesh([kpoints_mesh, kpoints_mesh, kpoints_mesh])

parentcalc = QepwCalc.get_subclass_from_pk(parent_id)

structure = parentcalc.inp.structure
parent_folder = parentcalc.out.remote_folder

code = parentcalc.get_code()
calc = code.new_calc()
calc.set_max_wallclock_seconds(30*60) # 30 min
calc.set_resources({"num_machines": 1,'num_mpiprocs_per_machine':8})
if queue is not None:
    calc.set_queue_name(queue)
calc.use_parameters(parameters)
calc.use_parent_folder(parent_folder)
calc.use_kpoints(kpoints)
calc.use_structure(structure)
calc.use_pseudos_from_family(pseudo_family)
calc.use_settings(settings)

######

if submit_test:
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
        calc.uuid, calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)

