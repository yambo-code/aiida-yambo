#script to run aiida and gw100#
from __future__ import absolute_import

from aiida.orm import Dict, Str, load_node, KpointsData, Group, StructureData,QueryBuilder, Int, Bool
from aiida.plugins import CalculationFactory, DataFactory
from aiida_yambo.utils.common_helpers import *
from aiida_yambo.utils.parallelism_finder import *

import ase
from ase.io.xyz import read_xyz
from ase.io import read
from ase import Atoms
import os
import pandas as pd
import re 
import json

from ase import Atoms
from ase.visualize import view
from aiida.common import constants
from aiida_yambo.utils.parallelism_finder import *

def build_builder(molecule, para_space, parent_pk=None, precalc_done=False, copy=False):
    
    space=para_space
    spaces=para_space
    partition = 'm100_usr_prod'
    account = 'cin_preM100'
    Dict = DataFactory('dict')
    qb = QueryBuilder()
    qb.append(Group, filters={'label':{'like':'GW100%'}}, tag ='g') #tag così di sotto lo riconosco
    
    qb.append(StructureData, filters={'label':{'like':molecule}}, with_group='g')
    st = qb.all()[0][0]
    print('structure detected')
    
    qb.append(Dict, filters={'label':{'like':molecule+'_info'}}, with_group='g')
    mol = qb.all()[0][0].get_dict()    
    print('running molecule info', mol)

    nvalence = mol[molecule]['valence']
    print('valence is ', nvalence)

    list_ecut = []
    for i in st.get_kind_names():
        list_ecut.append(mol[molecule]['cutoff(Ry)']['standard'][i])
    ecut_dft = max(list_ecut)+5
    print('ecut_dft(Ry) = {}'.format(ecut_dft))
    bands_dft = 4000
    bands_gw = 4000
    cutoff_G = 2
    homo = int(nvalence/2)
    lumo = int(nvalence/2 + 1)

    print('homo and lumo: {}  {}'.format(homo,lumo))

    pw_code = load_node(9139)
    yambo_gpu_git2 = load_node(9484)
    yambo_gpu = yambo_gpu_git2 #load_node(9285)
    
    p2y_gpu = load_node(9286)
    
    nodes_scf = 1
    mpi_scf=4
    threads_scf=32

    nodes_nscf = 4
    mpi_nscf=4
    threads_nscf=32
    
    nodes_pre = 1
    mpi_pre = 4
    threads_pre = 32

    nodes_gw = 8
    mpi_gw=4
    threads_gw=32

    if 1:
        c=mpi_gw/2
        v=1

        options_scf = {
            'max_wallclock_seconds': 2 * 60 * 60,
            'resources': {
                "num_machines": nodes_scf,
                "num_mpiprocs_per_machine":mpi_scf,
                "num_cores_per_mpiproc":threads_scf,
            },
            'queue_name':partition, #partition
            'account':account,
            'job_name':molecule+'_pw',
            }
        
        options_nscf = {
            'max_wallclock_seconds': 9 * 60 * 60,
            'resources': {
                "num_machines": nodes_nscf,
                "num_mpiprocs_per_machine":mpi_nscf,
                "num_cores_per_mpiproc":threads_nscf,
            },
            'queue_name':partition, #partition
            'account':account,
            'job_name':molecule+'_pw',
            }

        options_pre = {
            'max_wallclock_seconds': 10 *60 * 60,
            'resources': {
                "num_machines": nodes_pre,
                "num_mpiprocs_per_machine":mpi_pre,
                "num_cores_per_mpiproc":threads_pre,
            },
            'queue_name':partition, #partition
            'account':account,
            'job_name':molecule+'_pw',
            }
    
        options_gw = {
            'max_wallclock_seconds': int(1.5*60 * 60),
            'resources': {
                "num_machines": nodes_gw,
                "num_mpiprocs_per_machine": mpi_gw,
                "num_cores_per_mpiproc": threads_gw,
            },
            'queue_name':partition, #partition
            'account':account,
            'job_name':molecule+'_pw',
            }

        settings_dict_scf = {
            #'parent_folder_symlink': True,
            'gamma_only': True, #typically twice faster
            #'cmdline': ['-C','mc'],
        }
    
    settings_dict_nscf = settings_dict_scf

    csc = u"#SBATCH --mem=230GB \n#SBATCH --gres=gpu:4"

    options_scf['custom_scheduler_commands'] = csc
    options_nscf['custom_scheduler_commands'] = csc 
    options_pre['custom_scheduler_commands'] = csc
    options_gw['custom_scheduler_commands'] = csc

    para_dict, res_gw=find_parallelism_qp(nodes=nodes_gw,mpi_per_node=mpi_gw,threads=threads_gw,bands=bands_gw,occupied=homo,
                             qp_corrected=2,kpoints=1,what=['bands'],last_qp=lumo,)
    #print(para_dict, res_gw)
    para_pre_dict, res_pre=find_parallelism_qp(nodes=nodes_pre,mpi_per_node=mpi_pre,threads=threads_pre,bands=bands_gw,
                                  occupied=homo,qp_corrected=2,kpoints=1,what=['bands'],last_qp=lumo,)
    #print(para_pre_dict, res_pre)
    para_dict['X_CPU'] = '1 1 2 16 1'
    para_dict['DIP_CPU'] = '1 32 1'
    para_dict['SE_CPU'] = '1 2 16'
 
    #print(para_dict, res_gw)

    options_gw['resources'].update(res_gw)
    print(options_gw['resources'])
    options_pre['resources'].update(res_pre)
    print(options_pre['resources'])

    Dict = DataFactory('dict')

    params_scf = {
        'CONTROL': {
            'calculation': 'scf',
            'verbosity': 'high',
            'wf_collect': True
        },
        'SYSTEM': {
            'ecutwfc': ecut_dft ,
            'force_symmorphic': True,
            'assume_isolated':'mt',
            'nbnd': lumo+10,
        },
        'ELECTRONS': {
            'conv_thr': 1.e-8,
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }

    parameters_scf = Dict(dict=params_scf)
    #parameter_scf.store()

###########################################################################

    params2 = {
        'CONTROL': {
            'calculation': 'nscf',
            'verbosity': 'high',
            'wf_collect': True,
            'restart_mode':'from_scratch'
        },
        'SYSTEM': {
            'ecutwfc': ecut_dft,
            'force_symmorphic': True,
            'nbnd': bands_dft,
            'assume_isolated':'mt',
        },
        'ELECTRONS': {
            'conv_thr': 1.e-8,
            'diagonalization': 'cg',
            'diago_thr_init': 5.0e-6,
            'diago_full_acc': True
        },
    }

    parameters_nscf = Dict(dict=params2)
    #parameter2.store()

##############################################################################

    parameter3 = {
        'ppa': True,
        'dyson':True,
        'gw0': True,
        'dipoles':True,
        'HF_and_locXC': True,
        'em1d': True,
        'Chimod': 'hartree',
        'rim_cut':True,
        #'RandQpts':1000000,
        #'RandGvec':100,
        #'RandGvec_units':'RL',
        'CUTGeo': "sphere xyz",
        'CUTRadius':19,
        'BndsRnXp': [1, bands_gw],
        'NGsBlkXp': cutoff_G,
        'NGsBlkXp_units': 'Ry',
        'PPAPntXp': 20,
        'PPAPntXp_units': 'eV',
        'GTermKind':'BG',
        #'XTermKind':'BG',
        #'PAR_def_mode':'memory',
        'GbndRnge': [1, bands_gw],
        'DysSolver': "n",
        'QPkrange': [[1, 1, homo, lumo]],
    }
    parameter3.update(para_dict)
    parameters_gw = Dict(dict=parameter3)
    #parameters3.store()

##############################################################################

    parameterPRE = {
        'HF_and_locXC': True,
        'dipoles':True,
        'Chimod': 'hartree',
        'rim_cut':True,
        #'RandQpts':1000000,
        #'RandGvec':100,
        #'RandGvec_units':'RL',
        'CUTGeo': "sphere xyz",
        'CUTRadius':19,
        'BndsRnXp': [1, bands_gw],
        'NGsBlkXp': 2,
        'NGsBlkXp_units': 'Ry',
        'PPAPntXp': 20,
        'PPAPntXp_units': 'eV',
        'GTermKind':'BG',
#        'PAR_def_mode':'memory',
        'GbndRnge': [1, bands_gw],
        'DysSolver': "n",
        'QPkrange': [[1, 1, homo, lumo]],
        }
    parameterPRE.update(para_pre_dict)
    parameters_pre = Dict(dict=parameterPRE)
    #parameters3.store()

    from aiida_quantumespresso.utils.pseudopotential import validate_and_prepare_pseudos_inputs
    pseudo_family = 'pseudo-dojo'
    
    qb.append(KpointsData, filters={'label':{'like':'Gamma'}}, with_group='g')
    kpoints = qb.all()[0][0]

    from aiida_yambo.workflows.yamboconvergence import YamboConvergence

    builder = YamboConvergence.get_builder()

##################scf+nscf part of the builder
    builder.ywfl.scf.pw.structure = st
    builder.ywfl.scf.pw.parameters = parameters_scf
    builder.kpoints = kpoints
    builder.ywfl.scf.pw.metadata.options.max_wallclock_seconds = options_scf['max_wallclock_seconds']
    builder.ywfl.scf.pw.metadata.options.resources = options_scf['resources']
    #builder.ywfl.scf.pw.metadata.options.job_name = options_scf['job_name']
    builder.ywfl.scf.pw.metadata.options.queue_name = options_scf['queue_name']

    builder.ywfl.scf.pw.metadata.options.account=options_scf['account']

    builder.ywfl.scf.pw.settings=Dict(dict=settings_dict_scf)
    builder.ywfl.nscf.pw.structure = builder.ywfl.scf.pw.structure
    builder.ywfl.nscf.pw.parameters = parameters_nscf

    builder.ywfl.nscf.pw.metadata.options.max_wallclock_seconds = options_nscf['max_wallclock_seconds']
    builder.ywfl.nscf.pw.metadata.options.resources = options_nscf['resources']
    builder.ywfl.nscf.pw.metadata.options.queue_name = options_nscf['queue_name']

    builder.ywfl.nscf.pw.metadata.options.account=options_nscf['account']

    
    builder.ywfl.nscf.pw.settings=Dict(dict=settings_dict_nscf)

    builder.ywfl.scf.pw.code = pw_code
    builder.ywfl.nscf.pw.code = pw_code

    builder.ywfl.scf.pw.metadata.options.custom_scheduler_commands = options_scf['custom_scheduler_commands']
    builder.ywfl.nscf.pw.metadata.options.custom_scheduler_commands = options_nscf['custom_scheduler_commands']
    builder.ywfl.yres.yambo.metadata.options.custom_scheduler_commands = options_gw['custom_scheduler_commands']
    builder.precalc.yres.yambo.metadata.options.custom_scheduler_commands = options_gw['custom_scheduler_commands']

    builder.ywfl.scf.pw.pseudos = validate_and_prepare_pseudos_inputs(
            builder.ywfl.scf.pw.structure, pseudo_family = Str(pseudo_family))
    builder.ywfl.nscf.pw.pseudos = builder.ywfl.scf.pw.pseudos

##################yambo part of the builder
#########################HF
    builder.precalc.scf=builder.ywfl.scf
    builder.precalc.nscf=builder.ywfl.nscf
    builder.precalc.yres.yambo.metadata.options.max_wallclock_seconds = options_pre['max_wallclock_seconds']
    builder.precalc.yres.yambo.metadata.options.resources = options_pre['resources']
    builder.precalc.yres.yambo.metadata.options.queue_name = options_pre['queue_name']

    builder.precalc.yres.yambo.metadata.options.account=options_pre['account']
    
    builder.precalc.yres.yambo.parameters = parameters_pre
    builder.precalc.yres.yambo.precode_parameters = Dict(dict={'-b':'250 '}) #-b':250
    builder.precalc.yres.yambo.settings = Dict(dict={'INITIALISE': False,})

    builder.precalc.yres.yambo.preprocessing_code = p2y_gpu
    builder.precalc.yres.yambo.code = yambo_gpu
#########################GW
    builder.ywfl.yres.yambo.metadata.options.max_wallclock_seconds = options_gw['max_wallclock_seconds']
    builder.ywfl.yres.yambo.metadata.options.resources = options_gw['resources']
    builder.ywfl.yres.yambo.metadata.options.queue_name = options_gw['queue_name']

    builder.ywfl.yres.yambo.metadata.options.account=options_gw['account']

    builder.ywfl.yres.max_iterations = Int(3)
    builder.ywfl.yres.clean_workdir = Bool(True)
    builder.precalc.yres.max_iterations = Int(3)
    builder.ywfl.yres.code_version = Str('4.1')
    builder.precalc.yres.code_version = Str('4.1')
    
    builder.ywfl.yres.yambo.parameters = parameters_gw
    builder.ywfl.yres.yambo.precode_parameters = Dict(dict={'-b':'250 '}) #-b':250
    builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False,'COPY_DBS':False})

    builder.ywfl.yres.yambo.preprocessing_code = p2y_gpu
    builder.ywfl.yres.yambo.code = yambo_gpu

    builder.p2y = builder.precalc
    builder.p2y['yres']['yambo']['preprocessing_code']  = p2y_gpu
    builder.p2y['yres']['yambo']['code'] =  yambo_gpu_git2
    builder.p2y['yres']['yambo']['metadata'] = builder.ywfl.scf.pw.metadata

    #builder.parent_folder = load_node(10904).outputs.remote_folder #2401 -b 250

    if parent_pk and precalc_done:
        builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False,'COPY_DBS':True})
        if 'RemoteData' in str(type(load_node(parent_pk))):
            builder.parent_folder = load_node(parent_pk)
        else:
            builder.parent_folder = load_node(parent_pk).outputs.remote_folder #2401 -b 250
        builder.workflow_settings = Dict(dict={'type':'2D_space',\
                                        'what':'single-levels','where':[(1,homo),(1,lumo)],\
                                        'where_in_words':['Gamma'],'PRE_CALC':False})
    elif parent_pk and copy:
        builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False,'COPY_DBS':True})
        if 'RemoteData' in str(type(load_node(parent_pk))):
            builder.parent_folder = load_node(parent_pk)
        else:
            builder.parent_folder = load_node(parent_pk).outputs.remote_folder #2401 -b 250
        builder.workflow_settings = Dict(dict={'type':'2D_space',\
                                        'what':'single-levels','where':[(1,homo),(1,lumo)],\
                                        'where_in_words':['Gamma'],'PRE_CALC':True})
    
    elif parent_pk:
        builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False,'COPY_DBS':False})
        if 'RemoteData' in str(type(load_node(parent_pk))):
            builder.parent_folder = load_node(parent_pk)
        else:
            builder.parent_folder = load_node(parent_pk).outputs.remote_folder #2401 -b 250
        builder.workflow_settings = Dict(dict={'type':'2D_space',\
                                        'what':'single-levels','where':[(1,homo),(1,lumo)],\
                                        'where_in_words':['Gamma'],'PRE_CALC':True})
    else:
        builder.ywfl.yres.yambo.settings = Dict(dict={'INITIALISE': False,'COPY_DBS':False})
        #builder.parent_folder = load_node(parent).outputs.remote_folder #2401 -b 250
        builder.workflow_settings = Dict(dict={'type':'2D_space',\
                                        'what':'single-levels','where':[(1,homo),(1,lumo)],\
                                        'where_in_words':['Gamma'],'PRE_CALC':True})

  
    #'what': 'single-levels','where':[(1,8),(1,9)]
    para_space = [{'var':['BndsRnXp','GbndRnge','NGsBlkXp'],
                    'space': spaces[0:1],'max_iterations': 1,},]

    para_space = []
    for i in range(0,len(space),2):
            para_space.append({'var':['BndsRnXp','GbndRnge','NGsBlkXp'],
                'space': space[i:i+2],'max_iterations': 1,})
        

    for i in range(len(para_space)):
        print('{}-th variable will be {}'.format(i+1,para_space[i]['var']))
        print('{}-th values will be {}'.format(i+1,para_space[i]['space']))
    builder.parameters_space = List(list = para_space)     

    return builder
