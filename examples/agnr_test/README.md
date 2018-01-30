
Getting Started HOWTO
=====================

1. Install AiiDA

2. Setup Computer

3. Setup Codes

4. Import pseudopotential


RUNNING
=======
From aiida_sample directory

`verdi run workflow.py --precode p2y4.2.1@marconisl   --yambocode yambo4.2.1@marconisl   --pwcode aqe6.2.1@marconisl    --pseudo  bench  --yamboconfig "../INPUTS/init_01.json"  --scfinput "../GS/scf.in"   --nscfinput  "../GS/nscf.in"`

