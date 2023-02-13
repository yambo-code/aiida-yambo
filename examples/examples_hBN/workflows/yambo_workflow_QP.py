#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys
import os
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import List, Dict, Str,UpfData
from aiida.engine import submit
from aiida_yambo.workflows.yambowf import YamboWorkflow
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
        '--QP',
        type=int,
        dest='QP',
        required=False,
        default=0,
        help='do you want to compute a set of QP?')

    args = parser.parse_args()

    ###### setting the machine options ######
    options = {
        'yambocode_id': args.yambocode_id,
        'yamboprecode_id': args.yamboprecode_id,
        'pwcode_id': args.pwcode_id,
        'pseudo_family': args.pseudo_family,
        'max_wallclock_seconds': args.max_wallclock_seconds,
        'QP':args.QP,
        'resources': {
            "num_machines": args.num_machines,
            "num_mpiprocs_per_machine": args.num_mpiprocs_per_machine,
            "num_cores_per_mpiproc": args.num_cores_per_mpiproc,
        },
        'prepend_text': u"export OMP_NUM_THREADS="+str(args.num_cores_per_mpiproc),
        }

    if args.parent_pk:
        options['parent_pk']=args.parent_pk

    if args.queue_name:
        options['queue_name']=args.queue_name

    if args.qos:
        options['qos']=args.qos

    if args.account:
        options['account']=args.account

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


    builder = YamboWorkflow.get_builder()


    ##################scf+nscf part of the builder
    builder.scf.pw.structure = structure
    builder.nscf.pw.structure = structure
    #builder.scf_parameters = parameter_scf
    builder.scf.kpoints = kpoints
    builder.nscf.kpoints = kpoints
    builder.scf.pw.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.scf.pw.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.scf.pw.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.scf.pw.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.scf.pw.metadata.options.account = options['account']

    builder.scf.pw.metadata.options.prepend_text = options['prepend_text']

    builder.scf.pw.parameters = Dict(dict=params_scf)
    builder.nscf.pw.parameters = Dict(dict=params_nscf)

    builder.nscf.pw.metadata = builder.scf.pw.metadata

    builder.scf.pw.code = load_code(options['pwcode_id'])
    builder.nscf.pw.code = load_code(options['pwcode_id'])

    family = load_group(options['pseudo_family'])
    builder.scf.pw.pseudos = family.get_pseudos(structure=structure) 
    builder.nscf.pw.pseudos = family.get_pseudos(structure=structure) 

    ##################yambo part of the builder
    builder.yres.yambo.metadata.options.max_wallclock_seconds = \
            options['max_wallclock_seconds']
    builder.yres.yambo.metadata.options.resources = \
            dict = options['resources']

    if 'queue_name' in options:
        builder.yres.yambo.metadata.options.queue_name = options['queue_name']

    if 'qos' in options:
        builder.yres.yambo.metadata.options.qos = options['qos']

    if 'account' in options:
        builder.yres.yambo.metadata.options.account = options['account']

    builder.yres.yambo.parameters = params_gw
    builder.yres.yambo.precode_parameters = Dict(dict={})
    builder.yres.yambo.settings = Dict(dict={'INITIALISE': False, 'COPY_DBS': False, 'T_VERBOSE':True,})
    builder.yres.max_iterations = Int(2)

    builder.additional_parsing = List(list=['gap_','G_v','gap_GG','gap_GY','gap_GK','gap_KK','gap_GM'])

    builder.yres.yambo.preprocessing_code = load_code(options['yamboprecode_id'])
    builder.yres.yambo.code = load_code(options['yambocode_id'])
    try:
        builder.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
    except:
        pass


    ############ QP JUNGLE ##################
    '''
    The idea is to split the QP calculation in several subsets, then merge it in a final database -- with yambopy functionalities.
    There are a lot of possibilities to run QP calculations, to be provided in the QP_subset_dict input of the YamboWorkflow: 
    
    (1) provide subset of already wanted QP, already in subsets (i.e. already splitted);

    QP_subset_dict= {
        'subsets':[
            [[1,1,8,9],[2,2,8,9]], #first subset
            [[3,3,8,9],[4,4,8,9]], #second subset
                   ],
    }


    (2) provide explicit QP, i.e. a list of single QP to be splitted;

    QP_subset_dict= {
        'explicit':[
            [1,1,8,9],[2,2,8,9],[3,3,8,9],[4,4,8,9], #to be splitted
                   ],
    }

    (3) provide boundaries for the bands to be computed: [ki,kf,bi,bf];

    QP_subset_dict= {
        'boundaries':{
            'ki':1,    #default=1
            'kf':20,   #default=NK_ibz
            'bi':8,
            'bf':9,
        },
    }

    (4) provide a range of (DFT) energies where to consider the bands and the k-points to be computed, useful if we don't know the system;
        of we want BSE for given energies -- usually, BSE spectra is well converged for 75% of this range. These are generated as 
        explicit QP, then splitted.
        It is possible to provide also: 'range_spectrum', which find the bands to be included in the BSE calculation, including the other bands 
        outside the range_QP window as scissored -- automatically by yambo in the BSE calc. So the final QP will have 
        rangeQP bands, but the BSE calc will have all the range_spectrum bands.
        These ranges are windows of 2*range, centered at the Fermi level. 
        If you set the key 'full_bands'=True, all the kpoints are included for each bands. otherwise, only the qp in the window.

    QP_subset_dict= {
        'range_QP':3, #eV         , default=nscf_gap_eV*1.2
        'range_spectrum':10, #eV

    }
    
    for (2) and (4) there are additional options:
        (a) 'split_bands': split also in bands, not only kpoints the subset. default is True.
        (b) 'extend_QP': it allows to extend the qp after the merging, including QP not explicitely computed
            as FD+scissored corrections (see paper HT M Bonacci et al. 2023). Useful in G0W0 interpolations
            e.g. within the aiida-yambo-wannier90 plugin.
            (b.1) 'consider_only': bands to be only considered explcitely, so the other ones are deleted from the explicit subsets;
            (b.2) 'T_smearing': the fake smearing temperature of the correction.

    QP_subset_dict.update({
        'split_bands':True, #default
        'extend_QP': True, #default is False
        'consider_only':[8,9],
        'T_smearing':1e-2, #default
    })
    
    computation options: 

    (a) 'qp_per_subset':20; #how many qp in each splitted subset.
    (b) 'parallel_runs':4; to be submitted at the same time remotely. then the remote is deleted, as the qp is stored locally,
    (c) 'resources':para_QP, #see below
    (d) 'parallelism':res_QP, #see below
    '''

    para_QP = {}
    para_QP['SE_CPU'] = '2 2 4'
    para_QP['SE_ROLEs'] = 'q qp b'
    res_QP = {
                            'num_machines': 1,
                            'num_mpiprocs_per_machine': 16,
                            'num_cores_per_mpiproc': 1,
                }
    
    
    QP_subset_dict= {
        'range_QP':10, #eV         , default=nscf_gap_eV*1.2
        'full_bands':True,
        'consider_only':[7,8,9,10], #eV
        'qp_per_subset': 20,
        'parallel_runs':4,

    }
    
    QP_subset_dict.update({
        'resources':res_QP, #default is the same as previous GW
        'parallelism': para_QP, #default is the same as previous GW

    })


    if options['QP']:
        builder.QP_subset_dict= Dict(dict=QP_subset_dict) #set this if you want to compute also QP after the single GW calculation.

    return builder

if __name__ == "__main__":
    options = get_options()
    builder = main(options)
    running = submit(builder)
    print("Submitted YamboWorkflow workchain; with pk=< {} >".format(running.pk))
