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

    return options

def main(options):

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
            'ecutwfc': 60.,
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

    params_nscf = {
        'CONTROL': {
            'calculation': 'nscf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': 60.,
            'force_symmorphic': True,
            'nbnd': 300
        },
        'ELECTRONS': {
            'mixing_mode': 'plain',
            'mixing_beta': 0.6,
            'conv_thr': 1.e-8,
            'diagonalization': 'david',
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }


    parameter_nscf = Dict(dict=params_nscf)

    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([8,8,1])

    ###### setting the lattice structure ######

    alat = 9.17865990871*0.529177 # Angstrom
    the_cell = [[1.000000*alat,   0.000000,   0.000000],
                [-0.500000*alat,  0.866025*alat,   0.000000],
                [0.000000,   0.000000,  3.2*alat]]

    atoms = Atoms('CCCCCCNN',
    [(0.502355208*alat,   0.550236753*alat,   0.0),
    (0.252424145*alat,   0.694521005*alat,   0.0),
    (0.002507615*alat,   0.550234737*alat,   0.0),
    (0.002510406*alat,   0.261657594*alat,   0.0),
    (0.252429688*alat,   0.117353190*alat,   0.0),
    (0.502366692*alat,   0.261640955*alat,   0.0),
    (-0.247619414*alat,  0.694645605*alat,   0.0),
    (0.752387961*alat,   0.117291062*alat,   0.0)],
    cell = [1,1,1])
    atoms.set_cell(the_cell, scale_atoms=False)
    atoms.set_pbc([True,True,False])

    StructureData = DataFactory('structure')
    structure = StructureData(ase=atoms)


    StructureData = DataFactory('structure')
    structure = StructureData(ase=atoms)




    params_gw = {'arguments':['rim_cut', 'dipoles', 'gw0', 'HF_and_locXC', 'ppa'],
                 'variables':{
                'GTermEn': [250.0, 'mHa'],
                'NGsBlkXp': [1.0, 'Ry'],
                'PPAPntXp': [30.0, 'eV'],
                'CUTRadius': [13.228083, ''],
                'CUTGeo': 'sphere xyz',
                'Chimod': 'hartree',
                'DysSolver': 'n',
                'GTermKind': 'BG',
                'BndsRnXp': [[1, 20], ''],
                'GbndRnge': [[1, 20], ''],
                'QPkrange': [[[1, 1, 4, 4,]], ''],
                }}

    params_gw = Dict(dict=params_gw)

    builder = YamboConvergence.get_builder()


    ##################scf+nscf part of the builder
    builder.ywfl.structure = structure
    builder.ywfl.scf_parameters = parameter_scf
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

    builder.ywfl.scf.pw.metadata.options.prepend_text = options['prepend_text']
    builder.ywfl.scf.pw.metadata.options.mpirun_extra_params = []
    #builder.precalc_inputs=params_p
    #builder.ywfl.nscf.pw.structure = builder.ywfl.scf.pw.structure
    #builder.ywfl.nscf.pw.parameters = parameter_nscf
    builder.ywfl.nscf.pw.metadata = builder.ywfl.scf.pw.metadata

    builder.ywfl.pw_code = load_code(options['pwcode_id'])
    builder.ywfl.pw_code = load_code(options['pwcode_id'])
    builder.ywfl.scf.pw.pseudos = validate_and_prepare_pseudos_inputs(
                 builder.ywfl.structure, pseudo_family = Str(options['pseudo_family']))    
    ##################yambo part of the builder

    try:
        builder.ywfl.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
    except:
        pass

        
    try:
        params_gw = load_node(options['inputparent_pk']).inputs.parameters
        print(params_gw.get_dict())
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

    builder.ywfl.yres.yambo.parameters = params_gw
    builder.ywfl.yres.yambo.precode_parameters = Dict(dict={})
    builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': False})
    builder.ywfl.yres.max_iterations = Int(3)
    builder.ywfl.yres.max_number_of_nodes = Int(0)


    builder.ywfl.yres.yambo.preprocessing_code = load_code(options['yamboprecode_id'])
    builder.ywfl.yres.yambo.code = load_code(options['yambocode_id'])

    builder.workflow_settings = Dict(dict={'type':'1D_convergence',
                                           'what':['gap_'],'bands_nscf_update':'all-at-once',
                                            })

    #'what': 'single-levels','where':[(1,8),(1,9)]
    var_to_conv = [{'var':'kpoint_mesh','delta': [2,2,0], 'max_iterations': 2, \
                                 'conv_thr': 0.1,},]

    var_to_conv = [{'var':['BndsRnXp','GbndRnge'],'delta': [[0,100],[0,100]],},]


    var_to_conv_dc =  [{'var':['BndsRnXp','GbndRnge'],'delta': [[0,10],[0,10]], 'steps': 3, 'max_iterations': 3, \
                                 'conv_thr': 0.2,'conv_window': 3},
                       {'var':'NGsBlkXp','delta': 1, 'steps': 3, 'max_iterations': 3, \
                                'conv_thr': 0.2,},
                       {'var':'kpoint_mesh','delta': [1,1,0], 'max_iterations': 3, \
                                 'conv_thr': 0.5,},]
    var_to_conv_hydra =  [{'var':['BndsRnXp','GbndRnge'],'delta': [[0,50],[0,50]], 'steps': 3, 'max_iterations': 3, \
                                 'conv_thr': 0.1,},
                   {'var':'NGsBlkXp','delta': 2, 'steps': 3, 'max_iterations': 3, \
                                'conv_thr': 0.1,},
                   {'var':['BndsRnXp','GbndRnge'],'delta': [[0,50],[0,50]], 'steps': 3, 'max_iterations': 5, \
                                 'conv_thr': 0.01,},
                   {'var':'NGsBlkXp','delta': 2, 'steps': 3, 'max_iterations': 5, \
                                 'conv_thr': 0.01,},
                   {'var':'kpoint_mesh','delta': [2,2,0], 'max_iterations': 3, \
                                 'conv_thr': 0.02,},]
                    
                    # 
                    # {'var':['BndsRnXp','GbndRnge'],'delta': [[0,20],[0,20]], 'steps': 2, 'max_iterations': 2, \
                      #           'conv_thr': 0.02, 'conv_window': 2},]
                  # {'var':'NGsBlkXp','delta': 2, 'steps': 3, 'max_iterations': 4, \
                  #              'conv_thr': 0.02, 'conv_window': 3},
                  # {'var':['BndsRnXp','GbndRnge'],'delta': [[0,100],[0,100]], 'steps': 3, 'max_iterations': 4, \
                  #               'conv_thr': 0.01, 'conv_window': 3},
                  #  {'var':'NGsBlkXp','delta': 2, 'steps': 3, 'max_iterations': 4, \
                  #              'conv_thr': 0.01, 'conv_window': 3},]
                   #{'var':['BndsRnXp','GbndRnge'],'delta': [[0,50],[0,50]], 'steps': 3, 'max_iterations': 5, \
                   #              'conv_thr': 0.05, 'conv_window': 3},
                   #{'var':'NGsBlkXp','delta': 2, 'steps': 3, 'max_iterations': 3, \
                   #              'conv_thr': 0.05, 'conv_window': 3},]
                   #{'var':'kpoint_density','delta': 1, 'steps': 2, 'max_iterations': 2, \
                    #             'conv_thr': 0.1, 'conv_window': 2}]

    '''
    builder.workflow_settings = Dict(dict={'type':'2D_space',
                                    'what':['direct_gap_eV,7_8_7_9'],
                                        })

    var_to_conv = [{'var':['BndsRnXp','GbndRnge','NGsBlkXp'],
                'space': [[[1, 50], [1, 50],2], [[1,60], [1, 60],4]],'max_iterations': 1,},]
    '''

    for i in range(len(var_to_conv_dc)):
        print('{}-th variable will be {}'.format(i+1,var_to_conv_dc[i]['var']))

    builder.parameters_space = List(list = var_to_conv_dc)


    #builder.parallelism_instructions = Dict(dict={'automatic' : True})

    dict_para_low = {}
    dict_para_low['X_CPU'] = '1 1 1 1 1'
    dict_para_low['X_ROLEs'] = 'q k g c v'
    dict_para_low['DIP_CPU'] = '1 1 1'
    dict_para_low['DIP_ROLEs'] = 'k c v'
    dict_para_low['SE_CPU'] = '1 1 1 1'
    dict_para_low['SE_ROLEs'] = 'q g qp b'

    dict_res_low = {
            "num_machines": 1,
            "num_mpiprocs_per_machine":1,
            "num_cores_per_mpiproc":1,
        }


    dict_para_normal = {}
    dict_para_normal['X_CPU'] = '1 2 1 8 1'
    dict_para_normal['X_ROLEs'] = 'q k g c v'
    dict_para_normal['DIP_CPU'] = '2 8 1'
    dict_para_normal['DIP_ROLEs'] = 'k c v'
    dict_para_normal['SE_CPU'] = '1 1 2 8'
    dict_para_normal['SE_ROLEs'] = 'q g qp b'

    dict_res_normal = {
            "num_machines": 4,
            "num_mpiprocs_per_machine":4,
            "num_cores_per_mpiproc":4,
        }


    builder_parallelism_instructions = Dict(dict={'manual' : {'low':{'BndsRnXp':[1,1200],
                                                                     'NGsBlkXp':[1,25],
                                                                     'kpoints':[1,300],
                                                                     'parallelism':dict_para_low,
                                                                     'resources':dict_res_low,
                                                                     },
                                                              }})

    return builder
    
if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    running.label = 'C3N test on hydra'
    print("Submitted YamboConvergence for C3N; with pk=< {} >".format(running.pk))
