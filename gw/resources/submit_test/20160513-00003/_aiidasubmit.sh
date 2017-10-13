#!/bin/bash

#PBS -r n
#PBS -m n
#PBS -N aiida-None
#PBS -V
#PBS -o _scheduler-stdout.txt
#PBS -e _scheduler-stderr.txt
#PBS -l walltime=00:30:00
#PBS -l select=1:mpiprocs=8
cd "$PBS_O_WORKDIR"


'mpirun' '-np' '8' '/home/marrazzo/espresso/bin/pw.x' '-in' 'aiida.in'  > 'aiida.out' 
