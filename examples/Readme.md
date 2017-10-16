Instructions
============

How to run the files in this folder: 
Create a structure,  and get the `pk`, 
To test the plugin from  SCF to GW, 
Run:  

```
verdi  run test_scf2yambo.py  --precode p2y_marconi@marconi  --yambocode yambo_marconi@marconi  --pwcode  qe5.4@marconi  --pseudo CHtest  --structure  569 --parent 898
```

To test the plugin from GW:
Run:  

```
verdi run test_yambo.py   --precode p2h@hyd   --yambocode yamb@hyd  --pwcode qegit@hyd  --pseudo CHtest  --parent   2197   --structure 7
```
passing the starting NSCF calculation `pk`. 


To test the single parameter convergence: 
Run,

```
verdi run test_convergence.py   --precode p2h@hyd   --yambocode yamb@hyd  --pwcode qegit@hyd  --pseudo CHtest  --parent 2205   --structure 7
```
where the parent is the   `NSCF` step to start from, open the test_convergence.py  to choose which parameter to converge. 


To test the FULL GW convergence:
Run,

```        
verdi run gwFullConvergence.py --precode p2y_marconi@marconi --yambocode yambo_marconi@marconi --pwcode qe5.4@marconi --pseudo CHtest --structure 569 --parent 963
```
The parent is the SCF  `pk` to start from. This will attempt to converge  K-points, Bands and Green's function cut-off
