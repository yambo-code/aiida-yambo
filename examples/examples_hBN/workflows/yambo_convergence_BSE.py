#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict
from aiida.engine import submit
from aiida_yambo.workflows.yamboconvergence import YamboConvergence
from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
from ase import Atoms
import argparse

def get_options():

    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    parser.add_argument(
        '--yambocode',
        type=str,
        dest='yambocode_id',
        required=True,
        help='The yambo(main code) codename to use')

    parser.add_argument(
        '--parent',
        type=int,
        dest='parent_pk',
        required=False,
        help='The parent to use')
    
    parser.add_argument(
        '--inputparent',
        type=int,
        dest='inputparent_pk',
        required=False,
        help='yambo input to use')

    parser.add_argument(
        '--yamboprecode',
        type=str,
        dest='yamboprecode_id',
        required=True,
        help='The precode to use')

    parser.add_argument(
        '--pwcode',
        type=str,
        dest='pwcode_id',
        required=True,
        help='The pw to use')

    parser.add_argument(
        '--pseudo',
        type=str,
        dest='pseudo_family',
        required=True,
        help='The pseudo_family')

    parser.add_argument(
        '--time',
        type=int,
        dest='max_wallclock_seconds',
        required=False,
        default=24*60*60,
        help='max wallclock in seconds')

    parser.add_argument(
        '--nodes',
        type=int,
        dest='num_machines',
        required=False,
        default=1,
        help='number of machines')

    parser.add_argument(
        '--mpi',
        type=int,
        dest='num_mpiprocs_per_machine',
        required=False,
        default=1,
        help='number of mpi processes per machine')

    parser.add_argument(
        '--threads',
        type=int,
        dest='num_cores_per_mpiproc',
        required=False,
        default=1,
        help='number of threads per mpi process')

    parser.add_argument(
        '--queue_name',
        type=str,
        dest='queue_name',
        required=False,
        default=None,
        help='queue(PBS) or partition(SLURM) name')

    parser.add_argument(
        '--qos',
        type=str,
        dest='qos',
        required=False,
        default=None,
        help='qos name')

    parser.add_argument(
        '--account',
        type=str,
        dest='account',
        required=False,
        default=None,
        help='account name')

    parser.add_argument(
        '--group_label',
        type=str,
        dest='group_label',
        required=False,
        default=None,
        help='group name')


    args = parser.parse_args()

    ###### setting the machine options ######
    options = {
        'yambocode_id': args.yambocode_id,
        'yamboprecode_id': args.yamboprecode_id,
        'pwcode_id': args.pwcode_id,
        'pseudo_family': args.pseudo_family,
        'max_wallclock_seconds': args.max_wallclock_seconds,
        'resources': {
            "num_machines": args.num_machines,
            "num_mpiprocs_per_machine": args.num_mpiprocs_per_machine,
            "num_cores_per_mpiproc": args.num_cores_per_mpiproc,
        },
        'prepend_text': u"export OMP_NUM_THREADS="+str(args.num_cores_per_mpiproc),
        }

    if args.parent_pk:
        options['parent_pk']=args.parent_pk

    if args.inputparent_pk:
        options['inputparent_pk']=args.inputparent_pk
        
    if args.queue_name:
        options['queue_name']=args.queue_name

    if args.qos:
        options['qos']=args.qos

    if args.account:
        options['account']=args.account
    
    if args.group_label:
        options['group_label']=args.group_label

    return options

def main(options):

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
            'ecutwfc': 80.,
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


    params_nscf = {
        'CONTROL': {
            'calculation': 'nscf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': 80.,
            'force_symmorphic': True,
            'nbnd': 100,
        },
        'ELECTRONS': {
            'mixing_mode': 'plain',
            'mixing_beta': 0.7,
            'conv_thr': 1.e-8,
            'diagonalization': 'david',
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }


    params_gw = {
        'arguments': [
            'dipoles',
            'HF_and_locXC',
            'dipoles',
            'gw0',
            'ppa',],
        'variables': {
            'Chimod': 'hartree',
            'DysSolver': 'n',
            'GTermKind': 'BG',
            'NGsBlkXp': [2, 'Ry'],
            'BndsRnXp': [[1, 50], ''],
            'GbndRnge': [[1, 50], ''],
            'QPkrange': [[[1, 1, 8, 9]], ''],}}


    params_gw = Dict(dict=params_gw)

    builder = YamboConvergence.get_builder()


    bse_params = {'arguments':['em1s','bse','bss','optics', 'dipoles',],
                'variables':{
                'BSEmod': 'resonant',
                'BSKmod': 'SEX',
                'BSSmod': 'd',
                'Lkind': 'full',
                'NGsBlkXs': [2, 'Ry'],
                'BSENGBlk': [2, 'Ry'],
                'Chimod': 'hartree',
                'DysSolver': 'n',
                'BEnSteps': [10,''],
                'BSEQptR': [[1,1],''],
                'BSEBands': [[8,9],''],
                'BEnRange': [[0.0, 10.0],'eV'],
                'BDmRange': [[0.1, 0.1],'eV'],
                'BLongDir': [[1.0, 1.0, 1.0],''],
                'LongDrXp': [[1.0, 1.0, 1.0],''],
                'LongDrXd': [[1.0, 1.0, 1.0],''],
                'LongDrXs': [[1.0, 1.0, 1.0],''],
                'BndsRnXs': [[1,50], ''],
                'KfnQP_E':[[1.5,1,1],''],
                'BS_CPU':str(int(options['resources']["num_machines"]*options['resources']["num_mpiprocs_per_machine"]/2))+' 2 1',
                'BS_ROLEs':'k eh t',
                },}

    builder.ywfl.yres.yambo.parameters = Dict(dict=bse_params)


    ##################scf+nscf part of the builder
    builder.ywfl.scf.pw.structure = structure
    builder.ywfl.nscf.pw.structure = structure
 

    builder.ywfl.scf.kpoints = kpoints
    builder.ywfl.nscf.kpoints = kpoints
    builder.ywfl.scf.pw.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.ywfl.scf.pw.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.ywfl.scf.pw.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.ywfl.scf.pw.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.ywfl.scf.pw.metadata.options.account = options['account']

    if 'group_label' in options:
        builder.group_label = Str(options['group_label'])
        
    builder.ywfl.scf.pw.metadata.options.prepend_text = options['prepend_text']
    builder.ywfl.scf.pw.metadata.options.mpirun_extra_params = []
    
    builder.ywfl.nscf.pw.parameters = Dict(dict=params_nscf)
    builder.ywfl.scf.pw.parameters = Dict(dict=params_scf)
    builder.ywfl.nscf.pw.metadata = builder.ywfl.scf.pw.metadata

    builder.ywfl.scf.pw.code = load_code(options['pwcode_id'])
    builder.ywfl.nscf.pw.code = load_code(options['pwcode_id'])
    family = load_group(options['pseudo_family'])
    builder.ywfl.scf.pw.pseudos = family.get_pseudos(structure=structure) 
    builder.ywfl.nscf.pw.pseudos = family.get_pseudos(structure=structure)   

    ##################yambo part of the builder

    try:
        builder.ywfl.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
    except:
        pass

    builder.ywfl.yres.yambo.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.ywfl.yres.yambo.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.ywfl.yres.yambo.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.ywfl.yres.yambo.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.ywfl.yres.yambo.metadata.options.account = options['account']
    
    builder.ywfl.yres.yambo.metadata.options = builder.ywfl.scf.pw.metadata.options

    builder.ywfl.yres.yambo.precode_parameters = Dict(dict={})
    builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': False})
    builder.ywfl.yres.max_iterations = Int(3)
    builder.ywfl.yres.max_number_of_nodes = Int(0)


    builder.ywfl.yres.yambo.preprocessing_code = load_code(options['yamboprecode_id'])
    builder.ywfl.yres.yambo.code = load_code(options['yambocode_id'])

    builder.ywfl.additional_parsing = List(list=['gap_'])

    builder.workflow_settings = Dict(dict={
        'type': 'cheap', #or heavy; cheap uses low parameters for the ones that we are not converging
        'what': ['lowest_exciton'],
        'bands_nscf_update': 'full-step'},)


    var_to_conv_dc = [
        {
            'var': ['kpoint_mesh'], 
            'start': [6,6,2], 
            'stop': [12,12,8], 
            'delta': [1, 1, 1], 
            'max': [14,14,10], 
            'steps': 4, 
            'max_iterations': 4, 
            'conv_thr': 25, 
            'conv_thr_units': '%', 
            'convergence_algorithm': 'new_algorithm_1D',
            },
            ] 
    

    dict_para_medium = {}
    dict_para_medium['X_and_IO_CPU'] = '2 1 1 8 1'
    dict_para_medium['X_and_IO_ROLEs'] = 'q k g c v'
    dict_para_medium['DIP_CPU'] = '1 16 1'
    dict_para_medium['DIP_ROLEs'] = 'k c v'
    dict_para_medium['SE_CPU'] = '1 2 8'
    dict_para_medium['SE_ROLEs'] = 'q qp b'

    dict_res_medium = {
            "num_machines": 1,
            "num_mpiprocs_per_machine":16,
            "num_cores_per_mpiproc":1,
        }
    
    dict_para_high = {}
    dict_para_high['X_and_IO_CPU'] = '2 1 1 8 1' 
    dict_para_high['X_and_IO_ROLEs'] = 'q k g c v'
    dict_para_high['DIP_CPU'] = '1 16 1'
    dict_para_high['DIP_ROLEs'] = 'k c v'
    dict_para_high['SE_CPU'] = '1 2 8'
    dict_para_high['SE_ROLEs'] = 'q qp b'

    dict_res_high = {
            "num_machines": 1,
            "num_mpiprocs_per_machine":16,
            "num_cores_per_mpiproc":1,
        }

    parallelism_instructions_manual = Dict(dict={'manual' : {                                                            
                                                              'std_1':{
                                                                     'BndsRnXp':[1,100],
                                                                     'NGsBlkXp':[2,18],
                                                                     'parallelism':dict_para_medium,
                                                                     'resources':dict_res_medium,
                                                                     },
                                                             'std_2':{
                                                                     'BndsRnXp':[101,1000],
                                                                     'NGsBlkXp':[2,18],
                                                                     'parallelism':dict_para_high,
                                                                     'resources':dict_res_high,
                                                                     },}})

    parallelism_instructions_auto = Dict(dict={'automatic' : {                                                            
                                                              'std_1':{
                                                                     'BndsRnXp':[1,100],
                                                                     'NGsBlkXp':[1,18],
                                                                     'mode':'balanced',
                                                                     'resources':dict_res_medium,
                                                                     },
                                                             'std_2':{
                                                                     'BndsRnXp':[101,1000],
                                                                     'NGsBlkXp':[1,18],
                                                                     'mode':'memory',
                                                                     'resources':dict_res_high,
                                                                     },}})
    

    builder.parallelism_instructions = parallelism_instructions_auto

    for i in range(len(var_to_conv_dc)):
        print('{}-th variable will be {}'.format(i+1,var_to_conv_dc[i]['var']))

    builder.parameters_space = List(list = var_to_conv_dc)
    

    builder.ywfl.qp = builder.ywfl.yres

    builder.ywfl.qp.yambo.parameters = params_gw


    

    return builder
    
if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    running.label = 'hBN test'
    print("Submitted YamboConvergence for bulk hBN; with pk=< {} >".format(running.pk))
