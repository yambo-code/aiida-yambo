# -*- coding: utf-8 -*-

from six.moves import range
import cmath
import netCDF4
import numpy
import copy
import glob, os, re

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

    #Game over...
    game_over = re.compile('Game')
    for line in log.lines:
        if game_over.findall(line):
            output_params['game_over'] = True

    #timing sections...
    time = re.compile('<([0-9hms]+)>')
    try:
        last_time = time.findall(log.lines[-1])[-1]
        output_params['last_time'] = yambotiming_to_seconds(last_time)
    except:
        last_time = 0
        output_params['last_time'] = 0


    timing = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] \[([0-9]+)\] [A-Za-z\s]+')
    timing_old = re.compile('^\s+?<([0-9a-z-]+)> \[([0-9]+)\] [A-Za-z\s]+')
    for line in log.lines:
        if timing.match(line):
            output_params['timing'].append(timing.match(line).string)
        elif timing_old.match(line):
            output_params['timing'].append(timing_old.match(line).string)
    #memstats...
    memory = re.compile('^\s+?<([0-9a-z-]+)> ([A-Z0-9a-z-]+)[:] (\[MEMORY\]) ')
    memory_old = re.compile('^\s+?<([0-9a-z-]+)> (\[MEMORY\]) ')
    alloc_error = re.compile('[ERROR]Allocation')
    incomplete_para_error = re.compile('[ERROR]Incomplete')
    impossible_para_error = re.compile('[ERROR]Impossible')
    for line in log.lines:
        if memory.match(line):
            output_params['memstats'].append(memory.match(line).string)
        elif memory_old.match(line):
                output_params['memstats'].append(memory_old.match(line).string)
        elif  alloc_error.findall(line):
            output_params['memory_error'] = True
        elif  incomplete_para_error.findall(line) or impossible_para_error.findall(line):
            output_params['para_error'] = True


    #just p2y...
    p2y_completed = re.compile('P2Y completed')
    for line in log.lines:
        if p2y_completed.findall(line):
            output_params['p2y_completed'] = True
            return output_params
            
    return output_params

def parse_report(report, output_params):
    #Game over...
    game_over = re.compile('Game')
    for line in report.lines:
        if game_over.findall(line):
            output_params['game_over'] = True

def parse_scheduler_stderr(stderr, output_params):

    m1 = re.compile('out of memory')
    m2 = re.compile('segmentation')
    m3 = re.compile('dumped')
    t1 = re.compile('walltime')
    for line in stderr.lines:
        if m1.findall(line) or m2.findall(line) or m3.findall(line):
            output_params['memory_error'] = True
        elif t1.findall(line):
            output_params['time_error'] = True