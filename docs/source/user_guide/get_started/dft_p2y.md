(dft_p2y)=

# Ground state properties

The following part explains how to run the density functional theory (DFT) simulations, using as example
the hexagonal boron nitride (hBN). 
The starting point is a self-consistent field (SCF) calculation of the electronic density, 
and then a calculation of the electronic wavefunctions through a non-self-consistent (NSCF) DFT calculation. 
So, the first AiiDA plugin used here is *aiida-quantumespresso*. 


## SCF step (Quantum ESPRESSO)

Using the `aiida-quantumespresso` plugin, we begin with the submission of an SCF calculation.
We are going to use the ``pk`` of the SCF 
calculation in the next step (NSCF). The ``pk`` is the number that identifies the corresponding node 
in the AiiDA database, and can be accessed via:
```bash
In  [1]: given_node.pk
Out [2]: 1234  #pk of the node here named "given_node".
```
We use the PwBaseWorkChain to submit a pw calculation, 
in such  a way to have automatic
error handling and restarting from failed runs. 

For details on how to use the aiida-quantumespresso plugin, please refer to the corresponding documentation. Remember to replace the codename
and pseudo-family with those configured in your AiiDA installation. NB: Yambo can be used only with norm-conserving pseudopotentials!

The example script to run an scf calculation is the one contained in aiida_yambo/examples_hBN/ground_state/scf_baseWorkchain.py.

As you can notice, we use the "argparse" module to provide some inputs from the command line, like the code and the pseudos to be used in
the simulation. In practice, the command to be run would be like:

```bash
$ verdi run scf_baseWorkchain.py --code <pk of the pw code> --pseudo <name of the pseudofamily>
```

this is just one choice used to submit the calculation, it is possible also to do it interactively via jupyter notebooks, as shown in 
the dedicated examples for silicon.
 
## NSCF step (Quantum ESPRESSO) for G0W0

Using the ``pk``  of the  SCF calculation, we now run a NSCF calculation as the starting point for the GW calculation. 
Following the aiida_yambo/examples_hBN/ground_state/nscf_baseWorkchain.py example, we observe that the script is the same for the scf step, 
except adding the following line: 

```python
builder.pw.parent_folder = load_node(options['parent_pk']).outputs.remote_folder
```

where we are setting the ``pk``  of the  SCF calculation (options['parent_pk'], parsed from input with the argparse module).
Moreover, the parameters dictionary now contains usual inputs for NSCF calculations, namely the correct 'calculation': 'nscf' and 
'nbnd' parameters. 

```bash
$ verdi run nscf_baseWorkchain.py --code <pk of the pw code> --pseudo <name of the pseudofamily> --parent <scf pk>
```