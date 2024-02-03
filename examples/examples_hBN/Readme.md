Instructions
============

How to run the files in this folder: 
Some of the inputs are created in the script,
but others have to be provided during the launch. 
  
Run:
 
```bash
verdi  run scf_baseWorkchain.py --code pw-6.8@hydralogin --pseudo sg15 --queue_name s3par

verdi  run nscf_baseWorkchain.py --code pw-6.8@hydralogin --pseudo sg15 --queue_name s3par --parent 86290

verdi  run yambo_gw.py  --yamboprecode p2y-devel@hydralogin  --yambocode yambo-RIMW@hydralogin --queue_name s3par --parent 86304

verdi  run yambo_restart.py  --yamboprecode p2y-devel@hydralogin  --yambocode yambo-RIMW@hydralogin --queue_name s3par --parent 86304

verdi  run yambo_workflow_QP.py  --yamboprecode p2y-devel@hydralogin  --yambocode yambo-RIMW@hydralogin --queue_name s3par --parent 86304 --pwcode pw-6.8@hydralogin --pseudo sg15 --QP 0

verdi  run yambo_convergence.py  --yamboprecode p2y-devel@hydralogin  --yambocode yambo-RIMW@hydralogin --queue_name s3par --parent 86304 --pwcode pw-6.8@hydralogin --pseudo sg15
```