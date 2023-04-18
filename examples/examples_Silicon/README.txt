This is the tutorial for the aiida-yambo plugin (and a little bit of aiida-yambo-wannier90 one).

Supported calculations: HF, GW, BSE, IP-RPA optics.
Features: automated workflows, QP merging, Wannier90 interface.

The tutorial is structured in jupyter notebook, interactive python shells.
Prerequisite: at least read the AiiDA tutorial: https://aiida-tutorials.readthedocs.io/en/latest/
            

The tutorial should be in principle delivered within an AiiDA virtual machine (Quantum Mobile), 
in such a way to skip the AiiDA installation part. Anyway, it is possible to run it also on a
personal AiiDA installation (see the relative documentation on how to install it).
The tutorial supposes that you already have all codes and computer set up in your installation. 

(A) Brief pre-requisites instructions:

	(01_structures) We introduce how to parse structures from quantumespresso files and store them as 
	StructureData, to then be used in our calculations.

	(02_pseudos) We introduce how to store in the AiiDA database the pseudopotentials within the aiida-pseudo plugin.

	(03_groups) We introduce groups and how to use them in our calculations.

(B) Run aiida-yambo plugin!
	
	(1) YamboCalculation: simple/bare Yambo
		(1.1) how to inspect outputs





