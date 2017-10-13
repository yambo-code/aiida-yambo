#!/bin/bash

#SBATCH --no-requeue
#SBATCH --job-name="aiida-None"
#SBATCH --get-user-env
#SBATCH --output=_scheduler-stdout.txt
#SBATCH --error=_scheduler-stderr.txt
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --time=00:30:00


module load espresso/5.2.1/intel-15.0.2.164

'srun' '/ssoft/espresso/5.2.1/pw.x' '-in' 'aiida.in'  > 'aiida.out' 
