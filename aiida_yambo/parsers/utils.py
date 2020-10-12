# -*- coding: utf-8 -*-

from six.moves import range
import cmath
import netCDF4
import numpy
import copy
import glob, os, re

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


def parse_log(log, output_params):

    if 'p2y' in log.filename:    #just p2y...
        p2y_completed = re.compile('P2Y completed')
        for line in log.lines:
            if p2y_completed.findall(line):
                output_params['p2y_completed'] = True
    
    elif 'setup' in log.filename:
        pass
    
    else:
        #Game over...
        game_over = re.compile('Game')
        game_over_2 = re.compile('Clock:')
        for line in log.lines:
            if game_over.findall(line) or game_over_2.findall(line):
                output_params['game_over'] = True

        #timing sections...
        timing = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] \[([0-9]+)\] [A-Za-z\s]+')
        timing_old = re.compile('^\s+?<([0-9a-z-]+)> \[([0-9]+)\] [A-Za-z\s]+')
        for line in log.lines:
            if timing.match(line):
                output_params['timing'].append(timing.match(line).string)
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
        #warnings
        warning = re.compile('\[WARNING\]')      
        #memstats...
        memory = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] (\[MEMORY\]) ')
        memory_old = re.compile('^\s+?<([0-9a-z-]+)> (\[MEMORY\]) ')
        alloc1_error = re.compile('\[ERROR\]Allocation')
        #alloc2_error = re.compile('\[MEMORY\] Alloc')
        incomplete_para_error = re.compile('\[ERROR\]Incomplete')
        impossible_para_error = re.compile('\[ERROR\]Impossible')
        impossible_para_error2 = re.compile('\[ERROR\]USER parallel')
        time_probably = re.compile('Alloc Xo%blc_d')
        X_par_mem = re.compile('\[ERROR\]Allocation of X_par%blc_d failed')
        reading_explosion_of_memory = re.compile('Reading')
        for line in log.lines:
            if warning.match(line):
                output_params['warnings'].append(warning.match(line).string)
            elif memory.match(line):
                output_params['memstats'].append(memory.match(line).string)
            elif memory_old.match(line):
                    output_params['memstats'].append(memory_old.match(line).string)
            elif  alloc1_error.findall(line):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
            elif  incomplete_para_error.findall(line) or impossible_para_error.findall(line) or impossible_para_error2.findall(line):
                output_params['para_error'] = True
            elif time_probably.findall(line):
                output_params['errors'].append('time_most_prob')
        try:
            if  reading_explosion_of_memory.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('memory_general')
        except:
            pass
        try:
            if  X_par_mem.findall(log.lines[-1]):
                output_params['memory_error'] = True
                output_params['errors'].append('X_par_allocation')
        except:
            pass
        # if  alloc2_error.findall(log.lines[-1]):
        #    output_params['memory_error'] = True
        #    output_params['errors'].append('memory_general')
        
            
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
    m2 = re.compile('segmentation')
    m3 = re.compile('dumped')
    t1 = re.compile('walltime')
    t2 = re.compile('time')
    for line in stderr.lines:
        if m1.findall(line) or m2.findall(line) or m3.findall(line):
            output_params['memory_error'] = True
            output_params['errors'].append('memory_general') 
        elif t1.findall(line) or t2.findall(line):
            output_params['time_error'] = True

def yambo_wrote_dbs(output_params):
    if len(output_params['timing']) > 3:
        output_params['yambo_wrote_dbs'] = True
    else:
        output_params['yambo_wrote_dbs'] = False

def get_yambo_version(report, output_params):
    pass
