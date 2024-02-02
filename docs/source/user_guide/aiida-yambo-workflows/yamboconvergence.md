(yamboconvergence)=

# YamboConvergence: automated GW and BSE convergences

The highest level workflow is represented by the ``YamboConvergence`` workchain, 
which implements the full automation of the convergence algorithm described in [Bonacci, M., Qiao, J., Spallanzani, N. et al. Towards high-throughput many-body perturbation theory: efficient algorithms and automated workflows. npj Comput Mater 9, 74 (2023)](https://doi.org/10.1038/s41524-023-01027-2). 
Simulations are organized on the fly, without any external user intervention. 
The purpose of this new proposed convergence algorithm is to obtain an accurate converged 
result doing the least possible number of calculations. This is possible if a reliable description of the convergence space is achieved, resulting also in a 
precise guess for the converged point, i.e. the converged parameters. The description of the space is performed by fitting some calculations that the workchain runs. 
A simple functional form of the space is assumed:

.. math:: f(\textbf{x}) = \prod_i^N \left( \frac{A_i}{x_i^{\alpha_i}} + b_i \right)

In this way it is straightforward to compute first and second partial derivatives, and impose constraints on them to find the converged region of the space. 
The algorithm is specifically designed to solve the coupled convergence between 
summation over empty states (``BndsRnXp`` or ``BndsRnXs`` and ``GbndRnge`` for example) and PW expansion (``NGsBlkXp`` or ``NGsBlkXs``), but it can be used also to 
accelerate convergence tests with respect to the ``k-point mesh`` or ``FFTGvecs``, as we shall see later. 
Moreover, the quantities that we can converge are the ones that can be parsed by the 
``YamboWorkflow`` workchain: quasiparticle levels/gaps, and excitonic energies:

* 'gap_': gap as found from nscf calculation (may differ from the final GW band gap, in terms of value and k-point indexes);
* 'gap_GG': gap at the Gamma point;
* 'lowest_exciton': lowest exciton from BSE;
* 'brightest_exciton': brightest exciton from BSE.

An example of automatic convergence over a typical GW parameters is shown in aiida_yambo/examples_hBN/workflows/yambo_convergence.py. 
The format is similar with respect to the other launching scripts, but here you can notice the addition of several inputs.
We have to provide ``workflow_settings``, which encode some of the workflow logic:

```python
builder.workflow_settings = Dict(dict={
    'type': 'cheap', #or heavy; cheap uses low value for parameters (inputs ones) that we are not converging right now.
    'what': ['gap_'], #quantity to be converged
    'bands_nscf_update': 'full-step'},) #computes nscf band considering the full space to be explored in the iteration.
```

The workflow submitted here looks for convergence on different parameters. The iter is specified
with the input list ``parameters_space``. This is a list of dictionaries, each one representing a given phase of the investigation. 
If `type` is cheap, already converged parameters are overrided to be starting one, when convergence is performed on the other parameters. This done in order to have faster calculations.
Instead, if `type` is heavy, the parameters already converged are taken as the converged value. In this way, at the end of the convergence you will have already done the full converged 
calculation and you can start from there with post processing. 
The quantity that we converge in this example is the gap ('what':['gap_']). Please note that,
changing the k-point mesh, the k-points will change index, so the gap_ will change. A safer convergence quantity can be 'gap_GG', i.e. the band gap at the Gamma point. 
The workflow will take care of it and doesn't stop until all the quantities are
converged (or the maximum restarts are reached).

Going through the example, we see that a set of parameters is converged following the instructions given in the builder.parameters_space input.
For coupled parameters convergence:

```python
{
    'var': ['BndsRnXp', 'GbndRnge', 'NGsBlkXp'],
    'start': [50, 50, 2],                           #starting values
    'stop': [400, 400, 10],                         #maximum values for the first grid creation
    'delta': [50, 50, 2],                           #grid spacing
    'max': [1000, 1000, 36],                        #maximum values for the largest grid creation
    'steps': 6,                                     #steps/calculation per iteration. For ['BndsRnXp', 'GbndRnge', 'NGsBlkXp'], always 6
    'max_iterations': 8,                            #maximum attempts
    'conv_thr': 1,                                  #converge threshold
    'conv_thr_units': 'eV',                         #converge threshold units
    'convergence_algorithm': 'new_algorithm_2D',    #we are converging actually 2 parameters: bands and cutoff
}
```

for single parameter convergence, e.g. k-points mesh:

```python
{
        'var': ['kpoint_mesh'], 
        'start': [6,6,2], 
        'stop': [12,12,8], 
        'delta': [1, 1, 1], 
        'max': [14,14,10], 
        'steps': 4, 
        'max_iterations': 4, 
        'conv_thr': 25, 
        'conv_thr_units': '%',                       #convergence threshold units: The relative error with respect to the most converged value
        'convergence_algorithm': 'new_algorithm_1D', #1D algorithm
}
```

In case of converge of FFTGvecs parameters:

```python
    {
            'var': ['FFTGvecs'], 
            'start': 10, 
            'stop': 40, 
            'delta': 5, 
            'max': 80, 
            'steps': 4, 
            'max_iterations': 4, 
            'conv_thr': 25, 
            'conv_thr_units': '%',                       
            'convergence_algorithm': 'new_algorithm_1D', 
            }
```

A good convergence journey would be ['FFTGvecs'] -> ['BndsRnXp', 'GbndRnge', 'NGsBlkXp'] -> ['kpoint_mesh'].

The successful workflow will return the results of the convergence iterations, as well as a final converged calculation, from which we can parse the
converged parameters (they can be also found in the `infos` outputs of the workflow), and a complete story of all the calculations of the workflow with all the information provided.


To show how the convergence algorithm works, here we plot the convergences performed on 2D-hBN imposing a convergence threshold of 1% on the final gap. The convergence is 
performed with respect to ``NGsBlkXp`` (G_cut in the plot) and ``BndsRnXp`` = ``GbndRnge`` (Nb in the plot). 

.. figure:: ./images/2D_conv_hBN.png
    :width: 400px
    :align: center
    :height: 400px

We can observe that first simulations (black squares) are performed on a starting grid, the blue one. The algorithm decides then to perform another set of calculations on 
a shifted grid, as the fit perofmed to predict the space was not enough accurate. Next, a converged point is predicted, corresponding to the blue square, and it is explicitely computed. 
Using also the informations on that point, the algorithm understands that a new converged point can be the red one. This is then computed and verified to be the real converged one. In this 
way, convergence is efficiently achieved. 

All the calculations are automatically collected in a group, created using the structure formula, or can be collected in a specific pre-existing group if the input 
``builder.group_label`` is provided as Str datatype.

## Specific parameter-dependent resources and parallelism

As the value of the parameters increases, the calculations will become computationally more demanding.
So, it is possible to define parameter-dependent resources and parallelism instructions by providing the ``builder.parallelism_instructions`` dictionary input:

```python
dict_para_medium = {}
dict_para_medium['X_and_IO_CPU'] = '2 1 1 8 1'
dict_para_medium['X_and_IO_ROLEs'] = 'q k g c v'
dict_para_medium['DIP_CPU'] = '1 16 1'
dict_para_medium['DIP_ROLEs'] = 'k c v'
dict_para_medium['SE_CPU'] = '1 2 8'
dict_para_medium['SE_ROLEs'] = 'q qp b'

dict_res_medium = {
        "num_machines": 1,
        "num_mpiprocs_per_machine":16, 
        "num_cores_per_mpiproc":1,
    }


builder.parallelism_instructions = Dict(dict={'manual' : {                                                            
                                                            'std_1':{
                                                                    'BndsRnXp':[1,100],                      
                                                                    'NGsBlkXp':[2,18],
                                                                    'kpoints':[3*3*3/2,12*12*12/2],        #estimation of the number of kpoints in iBZ for 3x3x3 and 12x12x12 meshes
                                                                    'parallelism':dict_para_medium,
                                                                    'resources':dict_res_medium,
                                                                    },
                                                            'std_2':{
                                                                    'BndsRnXp':[101,1000],
                                                                    'NGsBlkXp':[2,18],
                                                                    'parallelism':dict_para_medium, #it can be different from the one above
                                                                    'resources':dict_res_medium,    #it can be different from the one above
                                                                    },}})
```

in the above case, you are setting manually the parallelism (by means of "dict_para_medium").
The two different directives, 'std_1' and 'std_2', are respectively followed if the parameter values (for all the indicated parameters)
It is possible also to define automatic parallelization directives:

```python    
dict_res_medium = {
        "num_machines": 1,
        "num_mpiprocs_per_machine":16,
        "num_cores_per_mpiproc":1,
    }

dict_res_medium = {
        "num_machines": 4,
        "num_mpiprocs_per_machine":16,
        "num_cores_per_mpiproc":1,
    }

builder.parallelism_instructions = Dict(dict={'automatic' : {                                                            
                                                            'std_1':{
                                                                    'BndsRnXp':[1,100],
                                                                    'NGsBlkXp':[1,18],
                                                                    'mode':'balanced',
                                                                    'resources':dict_res_medium,
                                                                    },
                                                            'std_2':{
                                                                    'BndsRnXp':[101,1000],
                                                                    'NGsBlkXp':[1,18],
                                                                    'mode':'memory',                  #memory savings
                                                                    'resources':dict_res_high,
                                                                    },}})
```

## Output analysis

The final converged parameters can be obtained from the output node 'infos':

```python
    load_node(<pk>).outputs.infos.get_dict()
```

in this way you can obtain something like:

```python
{
"BndsRnXp": 50.0,
"E_ref": 5.4920627477806,
"GbndRnge": 50.0,
"NGsBlkXp": 2.0,
"gap_": 5.5143629702825,
}
```

You can also access from shell the results by executing the command ``verdi data dict show <pk-of-infos-node>``.

The full convergence history can be parsed using the python Pandas library:

```python
import pandas as pd
history = run.outputs.history.get_dict()
history_table = pd.DataFrame(history)
history_table
```

The final converged value being

```python
history_table[history_table['useful']==True]
```