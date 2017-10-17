all: yambo   scftoyambo  convergence


yambo:
	verdi run test_yambo.py    --precode np2y_marconi@marconi  --yambocode nyambo_marconi@marconi  --pwcode qe5.4@marconi  --pseudo CHtest  --parent   9275

scftoyambo:
	 verdi  run test_scf2yambo.py  --precode np2y_marconi@marconi  --yambocode nyambo_marconi@marconi  --pwcode  qe5.4@marconi  --pseudo CHtest  --structure  569 --parent 898

convergence:
	verdi run gwFullConvergence.py --precode p2y_marconi@marconi --yambocode yambo_marconi@marconi --pwcode qe5.4@marconi --pseudo CHtest --structure 569 --parent 963
