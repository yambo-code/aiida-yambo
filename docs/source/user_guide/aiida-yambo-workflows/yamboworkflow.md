(yamboworkflow)=

# YamboWorkflow

The `YamboWorkflow`  is the core workchain of the plugin that takes care of performing all the steps needed in a typical Yambo simulation -- 
from preliminary self-consistent (SCF) and non-self-consistent (NSCF) DFT calculations to the actual GW (BSE) calculations, and the related post-processing. 
The workflow ensures a robust interoperability between DFT and MBPT codes (Quantum ESPRESSO and Yambo, respectively), and links subsequent calculations, 
interfacing the data automatically. In practice, YamboWorkflow encodes the specific flowchart underlying each requested calculation, and allows 
for its dynamic execution according to the instructions provided in input. This implies performing all the intermediate steps needed for a specific calculations 
without the need of instructing them explicitly, or, on the contrary, to skip some of the intermediate steps for which parent calculations are available, fully 
exploiting the YamboWorkflow provenance information. It uses the PwBaseWorkchain from `aiida-quantumespresso`
as a subworkflow to perform the first DFT part, if required, and the `YamboRestart` for the GW part. A smart logic is considered to understand what 
process has to be done to achieve success. If the previous calculation is not ``finished_ok``, the workflow will exit in a failed state: we suppose that 
the success of an input calculation is guaranteed by the BaseRestartWorkchain used at the lower level of the plugin. 

Example scripts are provided, respectively for GW and BSE: aiida_yambo/examples_hBN/workflows/yambo_workflow_QP.py, aiida_yambo/examples_hBN/workflows/yambo_workflow_BSE.py 

As you may notice, here the builder has a new attributes, referring to scf, nscf and yambo parts: this means that we are actually providing the inputs for 
respectively PwBaseWorkchain and YamboRestart. 
The only 'strict' YamboWorkflow input is now the ``parent_folder``. 
Moreover, it is possible to ask the workflow to compute and parse some specific quantities, like gaps, quasiparticle levels an exciton eigenvalues. 
This is possible by providing as input an `additional_parsing` AiiDA List:

```bash
   builder.additional_parsing = List(list=['gap_','gap_GG','homo','lumo']) #GW
   builder.additional_parsing = List(list=['lowest_exciton','brightest_exciton']) #BSE
```

In this way, the workflow will first analyze the nscf calculation, understand (if needed) where the gap is and then modify the YamboRestart inputs in such a way to have computed the corresponding gap at the GW level.
Then, the quantity is stored in a human-readable output Dict called `output_ywfl_parameters`.
In case of BSE calculation, we can ask in the additional parsing list for the lowest and/or the brightest excitons. If you have the ndb.QP (as SingleFileData, output of a YamboCalculation for example), you can provide it as 
input to the workflow and so run BSE on top of this database. See the example for a clear explanation of the inputs needed.

## YamboWorkflow for multiple QP calculations

Another quantity that we can compute within the `YamboWorkflow` is a set of QP evaluations. 
This are needed, e.g., for band interpolation and BSE calculations. It is possible to instruct the worlkflow to add 
this step by providing as input the `QP_subset_dict`. Several possibilities are available in this case. 

The idea is to split the QP calculation in several subsets, then merge it in a final database. So, at the end of the calculations, the ndb.QP databases are merged in only one database and exposed as a SingleFileData 
output (``merged_QP``, and, see below, also ``extended_QP``). The merging is done by using yambopy functionalities. 
There are a lot of possibilities to run QP calculations, to be provided in the QP_subset_dict input of the YamboWorkflow, as you can see in aiida_yambo/examples_hBN/workflows/yambo_workflow_QP.py: 
    
(1) provide subset of already wanted QP, already in subsets (i.e. already splitted);

```python
   QP_subset_dict= {
            'subsets':[
            [[1,1,8,9],[2,2,8,9]], #first subset
            [[3,3,8,9],[4,4,8,9]], #second subset
                   ],
    }
```

(2) provide explicit QP, i.e. a list of single QP to be splitted;

```python
   QP_subset_dict= {
        'explicit':[
            [1,1,8,9],[2,2,8,9],[3,3,8,9],[4,4,8,9], #to be splitted
                   ],
    }
```

(3) provide boundaries for the bands to be computed: [ki,kf,bi,bf];

```python
   QP_subset_dict= {
        'boundaries':{
            'ki':1,    #default=1
            'kf':20,   #default=NK_ibz
            'bi':8,
            'bf':9,
        },
    }
```

(4) provide a range of (DFT) energies where to consider the bands and the k-points to be computed, useful if we don't know the system; 
if we want BSE for given energies -- usually, BSE spectra is well converged for 75% of this range. These are generated as explicit QP, then splitted.
It is possible to provide also: 'range_spectrum', which find the bands to be included in the BSE calculation, including the other bands 
outside the range_QP window as scissored -- automatically by yambo in the BSE calc. So the final QP will have rangeQP bands, but the BSE calc will have all the range_spectrum bands. 
These ranges are windows of 2*range, centered at the Fermi level. 
If you set the key 'full_bands'=True, all the kpoints are included for each bands. otherwise, only the qp in the window.

```python
   QP_subset_dict= {
        'range_QP':3, #eV         , default=nscf_gap_eV*1.2
        'range_spectrum':10, #eV

    }
```

In the case of (2) and (4) there are additional options: (a) 'split_bands': split also in bands, not only kpoints the subset. default is True.
(b) 'extend_QP': it allows to extend the qp after the merging, including QP not explicitely computed as 
FD+scissored corrections (see supplementary information of the paper: M. Bonacci et al., 
`Towards high-throughput many-body perturbation theory: efficient algorithms and automated workflows`, arXiv:2301.06407). 
Useful in G0W0 interpolations e.g. within the aiida-yambo-wannier90 plugin. 
(b.1) 'consider_only': bands to be only considered explcitely, so the other ones are deleted from the explicit subsets; 
(b.2) 'T_smearing': the fake smearing temperature of the correction.
(b.3) 'Nb': n, #number of bands to be included in the final extended QP db(from 1st to nth);

For example:

```python
   QP_subset_dict.update({
        'split_bands':True, #default
        'extend_QP': True, #default is False
        'Nb': [20], #default: conduction + valence
        'consider_only':[8,9],
        'T_smearing':1e-2, #default; set 1e-10 if you want to include only scissor correction after the explicitly computed QP, i.e. non-smooth. 
    })
```

computation options: 

   (a) 'qp_per_subset':20; #how many qp are present in each splitted subset.
   (b) 'parallel_runs':4; to be submitted at the same time remotely. then the remote folder is deleted, and the ndb.QP database is stored locally,
   (c) 'resources':para_QP, #see in the example
   (d) 'parallelism':res_QP, #see in the example


## YamboWorkflow for BSE on top of QP

It is possible also to ask the `YamboWorkflow` to run BSE on top of a QP database not yet computed. A first GW QP calculation is performed.
Then the workflow understands, if not provided, what Q-index is needed to compute the excitonic properties (usually the one corresponding to the QP band gap) and the range of bands to be included in the BSE construction
of the BSE Hamiltonian (following the QP subsect dictionary as the previous section).

Following aiida_yambo/examples_hBN/workflows/yambo_workflow_QP_BSE.py example, we see that now the GW-QP inputs are all under the qp attribute.

In this example, for simplicity, we just put these qp inputs as the BSE (yres) ones - so resources, code etc. - , and then we change the parameters to be the one of G0W0:

```python
   builder.qp = builder.yres

   params_gw = {
        'arguments': [
            'dipoles',
            'HF_and_locXC',
            'dipoles',
            'gw0',
            'ppa',],
        'variables': {
            'Chimod': 'hartree',
            'DysSolver': 'n',
            'GTermKind': 'BG',
            'NGsBlkXp': [2, 'Ry'],
            'BndsRnXp': [[1, 50], ''],
            'GbndRnge': [[1, 50], ''],
            'QPkrange': [[[1, 1, 8, 9]], ''],}}

   params_gw = Dict(dict=params_gw)
   builder.qp.yambo.parameters = params_gw
```

Outputs inspection:
-------------------

Outputs can be inspected via:

```python
    load_node(<pk>).outputs.output_ywfl_parameters.get_dict()
```

you will obtain something like:

```python
    {'gap_': 1.1034224483307,
    'homo': -0.35414132157192,
    'lumo': 0.74928112675883,
    'gap_GG': 3.0791768224843,
    'homo_G': -0.35414132157192,
    'lumo_G': 2.7250355009124,
    'gap_dft': 0.57213595875502,
    'homo_dft': 0.0,
    'lumo_dft': 0.57213595875502,
    'gap_GG_dft': 2.5341893678784,
    'homo_G_dft': 0.0,
    'lumo_G_dft': 2.5341893678784}
```

There is also an automatic dictionary creation for what concerns useful NSCF info, which 
can be observed using load_node(<pk>).outputs.nscf_mapping.get_dict():

```python
    {'soc': False,
    'gap_': [[1, 1, 4, 4], [13, 13, 5, 5]],
    'gap_GG': [[1, 1, 4, 4], [1, 1, 5, 5]],
    'homo_k': 1,
    'lumo_k': 13,
    'valence': 4,
    'gap_type': 'indirect',
    'conduction': 5,
    'nscf_gap_eV': 0.572,
    'dft_predicted': 'semiconductor/insulator',
    'spin-resolved': False,
    'number_of_kpoints': 16}
```