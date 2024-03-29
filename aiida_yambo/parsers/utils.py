# -*- coding: utf-8 -*-

from six.moves import range
import cmath
import netCDF4
import numpy
import copy
import glob, os, re

from yambopy.dbs.excitondb import *
from yambopy.dbs.savedb import * 

def take_fermi_parser(file):  # calc_node_pk = node_conv_wfl.outputs.last_calculation

    for line in file:
        if '[X]Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[3]))
            ef = float(line.split()[3])
        if '[X] Fermi Level' in line:
            print('The Fermi level is {}'.format(line.split()[4]))
            ef = float(line.split()[4])

    return ef

def yambotiming_to_seconds(yt):
    t = 0
    th = 0
    tm = 0
    ts = 0
    if isinstance(yt, str):
        for i in yt.replace('-',' ').split():
         if 'h' in i:
             th = int(i.replace('h',''))*3600
         if 'm' in i:
             tm = int(i.replace('m',''))*60
         if 's' in i:
              ts = int(i.replace('s',''))
        t = th+tm+ts
        return t
    else:
        return yt


errors = {'memory_error':['\[ERROR\]Allocation','\[ERROR\] Allocation', '\[ERROR\]out of memory', '\[ERROR\] out of memory', '\[MEMORY\] Alloc','\[MEMORY\]Alloc'],
          'time_most_prob':['Alloc Xo%blc_d',],
          'para_error':['\[ERROR\]Incomplete','\[ERROR\]Impossible','\[ERROR\]USER parallel',
                         '\[NULL\]','\[ERROR\] Incomplete','\[ERROR\] Impossible','\[ERROR\] USER parallel',
                        
                        ],
                            

          'X_par_allocation':['\[ERROR\]Allocation of X_par%blc_d failed'],
          
         }

errors_raw = {'memory_error':[r'[ERROR]Allocation',r'[ERROR] Allocation', r'out of memory', r'[ERROR] out of memory', r'[MEMORY] Alloc',r'[MEMORY]Alloc'],
          'time_most_prob':[r'Alloc Xo%blc_d',],
          'para_error':[r'[ERROR]Incomplete',r'[ERROR]Impossible',r'[ERROR]USER parallel',
                         r'[NULL]',r'[ERROR] Incomplete',r'[ERROR] Impossible',r'[ERROR] USER parallel',
                        
                        ],
                            

          'X_par_allocation':[r'[ERROR]Allocation of X_par%blc_d failed'],
          
         }

def parse_log(log,output_params,timing):
    
    
    if 'p2y' in log.filename:    #just p2y...
        p2y_completed = re.compile('P2Y completed')
        for line in log.lines:
            if p2y_completed.findall(line):
                output_params['p2y_completed'] = True
    
    elif 'l_setup' in log.filename or 'l-setup' in log.filename:
        pass
    
    else:
        #Game over...
        game_over = re.compile('Game')
        game_over_2 = re.compile('Clock:')
        for line in log.lines:
            if game_over.findall(line) or game_over_2.findall(line):
                output_params['game_over'] = True
                break
            else:
                output_params['game_over'] = False
        #timing sections...
        timing_new = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] \[([0-9]+)\] [A-Za-z\s]+')
        timing_old = re.compile('^\s+?<([0-9a-z-]+)> \[([0-9]+)\] [A-Za-z\s]+')
        timing_bugs = re.compile('\[([0-9]+)\] [A-Za-z\s]+')
        #if output_params['timing'] == []:
        for line in log.lines:
            if timing_bugs.findall(line):
                output_params['timing'].append(line) #to fix for a better parsing
            elif timing_new.match(line):
                output_params['timing'].append(timing_new.match(line).string)
            elif timing_old.match(line):
                output_params['timing'].append(timing_old.match(line).string)
            
        time = re.compile('<([0-9hms-]+)>')
                
        try:
            last_time = time.findall(log.lines[-1])[-1]
            output_params['last_time'] = yambotiming_to_seconds(last_time)
        except:
            try:
                last_time = time.findall(output_params['timing'][-1])[-1]
                output_params['last_time'] = yambotiming_to_seconds(last_time)
            except:
                last_time = 0
                output_params['last_time'] = 0
        
        if timing:
            output_params['timing'].append('verbose_output:')
            t_verbose = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] (\[TIMING\])')
            t_verbose_old = re.compile('^\s+?<([0-9a-z-]+)> (\[TIMING\]) ')
            for line in log.lines:
                if t_verbose.match(line):
                    output_params['timing'].append(t_verbose.match(line).string)
                elif t_verbose_old.match(line):
                    output_params['timing'].append(t_verbose_old.match(line).string)
                    
        #warnings
        warning = re.compile('\[WARNING\]')      
        #memstats...
        memory = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] (\[MEMORY\]) ')
        memory_old = re.compile('^\s+?<([0-9a-z-]+)> (\[MEMORY\]) ')
        alloc1_error = re.compile('\[ERROR\]Allocation')
        alloc2_error = re.compile('\[MEMORY\] Alloc')
        alloc3_error = re.compile('\[MEMORY\]out of memory')
        alloc4_error = re.compile('\[MEMORY\] out of memory')
        incomplete_para_error = re.compile('\[ERROR\]Incomplete')
        impossible_para_error = re.compile('\[ERROR\]Impossible')
        impossible_para_error2 = re.compile('\[ERROR\]USER parallel')
        incomplete_para_error_ = re.compile('\[ERROR\] Incomplete')
        impossible_para_error_ = re.compile('\[ERROR\] Impossible')
        impossible_para_error2_ = re.compile('\[ERROR\] USER parallel')
        corrupted_fragment = re.compile('\[ERROR\] Writing File')
        time_probably = re.compile('Alloc Xo%blc_d')
        X_par_mem = re.compile('\[ERROR\]Allocation of X_par%blc_d failed')
        X_par_mem_ = re.compile('\[ERROR\] Allocation of X_par%blc_d failed')
        reading_explosion_of_memory = re.compile('Reading')
        for line in log.lines:
            if warning.match(line):
                output_params['warnings'].append(warning.match(line).string)
            if memory.match(line):
                output_params['memstats'].append(memory.match(line).string)
            if memory_old.match(line):
                    output_params['memstats'].append(memory_old.match(line).string)
            if  alloc1_error.findall(line):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
            if  alloc3_error.findall(line):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
            if  alloc4_error.findall(line):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
            if  incomplete_para_error.findall(line) or impossible_para_error.findall(line) or impossible_para_error2.findall(line):
                output_params['para_error'] = True
            if  incomplete_para_error_.findall(line) or impossible_para_error_.findall(line) or impossible_para_error2_.findall(line):
                output_params['para_error'] = True
            if time_probably.findall(line):
                output_params['errors'].append('time_most_prob')
            if corrupted_fragment.findall(line):
                output_params['errors'].append('corrupted_fragment')
                output_params['corrupted_fragment'] = re.findall("ndb.pp_fragment_[0-9]+",line)
        try:
            if  reading_explosion_of_memory.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
        except:
            pass
        
        try:
            if  alloc2_error.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
        except:
            pass

        try:
            if  alloc3_error.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
        except:
            pass

        try:
            if  alloc4_error.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
        except:
            pass
        
        try:
            if  X_par_mem.findall(log.lines[-1]) or X_par_mem_.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('X_par_allocation')
        except:
            pass

        if 'out of memory' in log.lines[-1]:
            output_params['memory_error'] = True
            output_params['errors'].append('memory_general')
            
    return output_params

def parse_report(report, output_params):
    
    try:
        output_params['Fermi(eV)'] = take_fermi_parser(report.lines)
    except:
        pass

    if 'setup' in report.filename:
        pass

    else:
        #Game over...
        game_over = re.compile('Game')
        game_over_2 = re.compile('Clock:')
        gpu_support = re.compile('CUDA')
        for line in report.lines:
            if game_over.findall(line) or game_over_2.findall(line):
                output_params['game_over'] = True
        
            if gpu_support.findall(line):
                output_params['has_gpu'] = True

def parse_scheduler_stderr(stderr, output_params):

    m1 = re.compile('out of memory')
    m1_1 = re.compile('out-of-memory')
    m2 = re.compile('Segmentation')
    m3 = re.compile('dumped')
    t1 = re.compile('walltime')
    t2 = re.compile('time')
    t3 = re.compile('TIME')
    for line in stderr.readlines():
        if m1.findall(line) or m1_1.findall(line) or m2.findall(line) or m3.findall(line):
            output_params['memory_error'] = True
            output_params['errors'].append('memory_general') 
        elif t1.findall(line) or t2.findall(line) or t3.findall(line):
            output_params['time_error'] = True

def yambo_wrote_dbs(output_params):
    if len(output_params['timing']) > 4:
        for step in output_params['timing']:
            if '[05]' in step:
                output_params['yambo_wrote_dbs'] = True
    else:
        output_params['yambo_wrote_dbs'] = False

def get_yambo_version(report, output_params):
    pass

def parse_BS(folder,filename, save_dir):
    q = filename[13:]
    lat  = YamboLatticeDB.from_db_file(filename=save_dir+'/ns.db1')
    ydb  = YamboExcitonDB.from_db_file(filename=filename,folder=folder,lattice=lat)
    chi = ydb.get_chi(emin=0, emax=20, estep=0.01, broad=0.15,)
    chi_ = {'eV':chi[0],'eps_2':chi[1].imag,'eps_1':chi[1].real}
    
    excitons = {'energies':ydb.eigenvalues.real,
               'intensities':ydb.get_intensities().real}
    
    
    
    return q, chi_, excitons