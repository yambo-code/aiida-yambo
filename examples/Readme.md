Instructions
============

How to run the files in this folder: 
Some of the inputs are created in the script,
but others have to be provided during the launch. 
To test the plugin for GW, 
Run:  

```
verdi  run yambo_gw.py  --precode <pk_p2y_code>  --code <pk_yambo_code> --parent <pk_parent_calc>
```

and so on. Read all the examples to know what are the inputs to provide for a given workchain or calculation. 
Examples:

verdi run yambo_gw.py --yambocode yambo-RIMW@hydralogin --parent 15084 --yamboprecode p2y-devel@hydralogin --queue_name s3par --mpi 16

verdi run yambo_restart.py --yambocode yambo-RIMW@hydralogin --parent 15084 --yamboprecode p2y-devel@hydralogin --queue_name s3par --mpi 16 

verdi run yambo_workflow.py --yambocode yambo-RIMW@hydralogin --yamboprecode p2y-devel@hydralogin --queue_name s3par --mpi 16 --pwcode pw-6.8@hydralogin --pseudo sg15

verdi run yambo_workflow_QP_BSE.py --yambocode yambo-RIMW@hydralogin --yamboprecode p2y-devel@hydralogin --queue_name s3par --mpi 16 --pwcode pw-6.8@hydralogin --pseudo sg15 --parent 15248

verdi run yambo_convergence.py --yambocode yambo-RIMW@hydralogin --yamboprecode p2y-devel@hydralogin --queue_name s3par --mpi 16 --pwcode pw-6.8@hydralogin --pseudo sg15
