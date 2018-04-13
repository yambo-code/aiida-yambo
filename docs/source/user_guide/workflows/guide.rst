.. _tut-ref-to-workflow_guide:

Yambo Workflows Usage Guide
===========================

.. toctree::
   :maxdepth: 2

The following documents the usage of the workflows provided by the  `aiida yambo` plugin.


YamboRestartWf 
--------------

This workflow will run a single yambo calculation, (P2Y or Yambo init, or Yambo run), with a tolerance
for failed calculations, and it will restart calculations that have failed due to 

- Time Exhaustion on the queue.
- Memory errors.
- Incorrect Parallism errors.
- Errors from a few select unphysical input like very low number of bands.

Inputs
~~~~~~
This workflow provides the following input options to the user,

- **precode**: this is provided to the plugin as the P2Y code,  type `Str`.
- **yambocode**: this is provided to the plugin as the YAMBO code, type `Str`.
- **calculation_set**: this provides the scheduler settings to the plugin, type `ParameterData`.
- **settings**: provides code specific settings, type `ParameterData`.
- **parent_folder**: the parent calculation's remote,  type `RemoteData`.
- **parameters**: yambo calculation input parameters, type `ParameterData`
- **restart_options**: workflow specific input, setting the number of max restarts: ie
  `{'max_restarts':4}`, decides how many times the workflow will restart failed calculations before
  aborting, type `ParameterData`, *not required*

Outputs
~~~~~~~

- **gw** `ParameterData` with two keys: consisting of  `"yambo_pk"` the calculation pk, and a Boolean "success" taking one of True or False, this is Depreciated and will be changed in future to remove the pk output for transferability reasons.
- **yambo_remote_folder** the RemoteData Node related to the completed calculation.


YamboWorkflow
--------------

This workflow will perform a full NSCF+GW calculation, accepting a set of PW and GW inputs. It uses the YamboRestartWf as a subworkflow.

Inputs
~~~~~~

- **restart_options_pw**: PW specific restart options i.e. `{"max_restarts":4}`, type `ParameterData`
- **restart_options_gw** : GW spefific restart options  i.e. `{"max_restarts":4}` , type `ParameterData`
- **codename_pw** : this is provided to the `PwRestartWf` subworkflow as the PW code,  type `Str`.
- **codename_p2y** : this is provided to the `YamboRestartWf` subworkflow as the P2Y code,  type `Str`.
- **codename_yambo** : this is provided to the `YamboRestartWf` subworkflow as the YAMBO code,  type `Str`.
- **pseudo_family** : Pseudo family name, type `Str`.
- **calculation_set_pw** : the scheduler settings i.e. `{'resources':{...}}`  for PW calculation, type `ParameterData`.
- **calculation_set_p2y** : the scheduler settings {'resources':{...}} for P2Y conversion, type `ParameterData`.
- **calculation_set_yambo** : scheduler settings {'resources':{...}} for Yambo calculation,  type `ParameterData`.
- **settings_pw** : plugin settings for PW,  type `ParameterData`.
- **settings_p2y** : settings for P2Y  i.e.  `{ "ADDITIONAL_RETRIEVE_LIST":[], 'INITIALISE':True}`  (optional),  type `ParameterData`.
- **settings_yambo** : settings for yambo i.e. `{ "ADDITIONAL_RETRIEVE_LIST":[] }` (optional),  type `ParameterData`.
- **structure** : Structure, type `StructureData`.
- **kpoint_pw** : kpoints  (optional), type `KpointsData`.
- **gamma_pw** : Whether its a gamma  point calculation (optional), type `Bool`,
- **parameters_pw** : PW SCF parameters , type `ParameterData`
- **parameters_pw_nscf** : PW NSCF specific parameters (optional), type `ParameterData`, when not provided the **parameters_pw** with
  modifications to `nbnd` and `calculation_type` changed 
- **parameters_p2y** : input parameters for P2Y, currently an empty `ParameterData`, needed since P2Y and YAMBO share the same plugin.
- **parameters_yambo** : Parameters for Yambo, type `ParameterData` .
- **parent_folder** : Parent calculation (optional), type `RemoteData`.
- **previous_yambo_workchain** : Parent workchain (Yambo) (optional), type `Str`, to restart from a previous workchain.
- **to_set_qpkrange** :  whether to set the QPkrange, setting defaults  (optional), the defaults will be `[(1, nkpts, VBM-1, CBM+1)]`,
   where VBM is at `nelec/2` and CBM is VBM+1, primarily used by the higher level Full convergence workflow YamboFullConvergenceWorkflow, type `Bool`
- **to_set_bands** : Whether to set the bands, overide with default (optional), defaults will be  `(1, nelec*6)`, type `Bool`
- **bands_groupname** :  (optional), used to group the outputs of the workchain under a label, type `Str`

outputs
~~~~~~~

The output consists of a `ParameterData` consisting of the following keys

- **gw** :  `ParameterData` from the GW subworkflow
- **pw** : `ParameterData` with outputs from the PW subworkflow
- **yambo_remote_folder**: `RemoteData` from GW calculation performed by YamboRestart subworkflow
- **scf_remote_folder**: `RemoteData` from PW calculation performed by PW subworkflow
- **nscf_remote_folder**: `RemoteData` from PW calculation performed by PW subworkflow


YamboConvergenceWorkflow
------------------------

This workflow converges a single parameter, and knows how to converge the following GW parameters,
the K-points, the Bands, the FFT grid and G-cutoff. Only one of these can be done at a time, and
only one must be provided. It uses the YamboWorkflow as a subworkflow.

Accepted Inputs
~~~~~~~~~~~~~~~

- **precode** : the yambo  P2Y converter code, type `Str` 
- **pwcode** :  the PW code, type `Str`
- **yambocode** : Yambo code, type `Str`
- **pseudo** :  pseudopotential family name, type `Str`
- **calculation_set_pw** : the scheduler settings {'resources':{...}} for the PW SCF step, type `ParameterData`.
- **calculation_set_pw_nscf** : the scheduler settings {'resources':{...}}  for the PW NSCF step, `ParameterData`.
- **calculation_set_p2y** : the scheduler settings {'resources':{...}} for the P2Y conversion step, type `ParameterData`.
- **calculation_set** : the scheduler settings {'resources':{...}}  for the Yambo calculation, type `ParameterData`.
- **parent_scf_folder** : Parent SCF calculation, (Optional) , type `RemoteData`.
- **settings_p2y** :  plugin settings for P2Y code,  type `ParameterData`.
- **settings** : plugin settings for Yambo code i.e. `{ "ADDITIONAL_RETRIEVE_LIST":[], 'INITIALISE':True}`.
- **settings_pw** :  plugin settings for PW SCF step, type `ParameterData`
- **settings_pw_nscf** :  plugin settings for PW NSCF step, type `ParameterData`
- **structure** : The Structure data, type `StructureData`
- **parent_nscf_folder** : Parent NSCF calculation (Optional),  type `RemoteData`
- **parameters_p2y** : input parameters for P2Y, type `ParameterData`
- **parameters** : input parameters for Yambo, type `ParameterData`
- **parameters_pw** : input parameters for  PW SCF ,  `ParameterData`
- **parameters_pw_nscf** : input parameters for PW NSCF , `ParameterData`
- **convergence_parameters** : the parameter to converge using 1-D line search, i.e
                               {'variable_to_converge':'bands' or 'W_cutoff' or 'kpoints' or 'FFT_cutoff',
                                'start_value': 10,
                                'step': 5,
                                'max_value':100,
                                'conv_tol': 0.1,
                                'conv_window': 3 (optional),
                                'loop_length': 4 (optional),
                                }, type `ParameterData`
- **restart_options_pw** :  PW specific restart options i.e. `{"max_restarts":4}`
- **restart_options_gw** :  GW specific restart options i.e. `{"max_restarts":4}`


Outputs
~~~~~~~

The output consists of a `ParameterData` consisting of the following keys

- **convergence** :  `ParameterData` with these keys: 
  `parameters`:  converged GW parameters.  
  `convergence_space`: data about the convergece behaviour.  
  `energy_widths`:  VBM-CBM gap widths. 
- **yambo_remote_folder**: `RemoteData` from GW calculation performed by YamboRestart subworkflow
- **scf_remote_folder**: `RemoteData` from PW calculation performed by PW subworkflow
- **nscf_remote_folder**: `RemoteData` from PW calculation performed by PW subworkflow


YamboFullConvergenceWorkflow
----------------------------                                                                                                                                                     

The full convergence workflow takes a set of minimal inputs, and as output returns the converged
parameters of a GW calculation. It uses as a subworkflow the YamboConvergenceWorkflow, and will
converge the  bands, Greens function cutoff, the FFT grid and K-point mesh. The method used is
the following:  
**First** Converge the kpoints  
**Then**  Converge the FFT with converged Kpoint inputs  
**Then**  Converge the Bands with converged Kpoint and FFT grid  
**Then**  Converge the G-cutoff with converged Bands, FFT and Kpoints.   
**Then**  Reconverge the Bands to achieve consistency between bands and G-cutoff  
**Then if** If previous is converged, end the full convergence  
**Then if** If previous is  **NOT** converged, repeat the G-cutoff with new Bands. (Repeat consistency check for Bands/G-cutoff co-convergence as neccessary).  


Accepted inputs
~~~~~~~~~~~~~~~

- **precode** : The P2Y converted code, type `Str` 
- **pwcode** : the PW code, type `Str`
- **yambocode** : the Yambo code, type `Str`
- **pseudo** : the pseudopotential family, type `Str`
- **threshold** : convergence threshold criteria, default is 0.1 (Gaps converged to 0.1 eV), type `Float`
- **parent_scf_folder** : PW SCF remote data, type `ParameterData`
- **parent_nscf_folder** : PW SCF remote data, type `ParameterData`
- **structure** :  Structure data,  type `StructureData`
- **calculation_set** : the scheduler settings for Yambo, type  `ParameterData`
- **calculation_set_pw** : the scheduler settings for PW, type `ParameterData`
- **calculation_set_pw_nscf** : the scheduler settings NSCF, type `ParameterData`
- **parameters** : input parameters for Yambo, `ParameterData`
- **parameters_pw** : input parameters for PW SCF, type `ParameterData`
- **parameters_pw_nscf** : input parameters for PW NSCF, type `ParameterData`
- **convergence_settings** : the start and end values for the variables to converge such as start and max FFT value, Bands, or kpoints, type `ParameterData`
- **restart_options_pw** : Settings controlling the restart behaviour of the PW subworkflows, type `ParameterData`
- **restart_options_gw** : Settings controlling the restart behaviour of GW subworkflows, type `ParameterData`
- **settings** :   plugin settings for Yambo code, type `ParameterData`
- **settings_p2y** :  plugin settings for P2Y code, type `ParameterData`
- **settings_pw** :  plugin settings for PW code, type `ParameterData`
- **settings_pw_nscf** :  plugin settings for PW code, type `ParameterData`


Outputs
~~~~~~~

The output consists of a `ParameterData` consisting of the following keys

- **kpoints** :  The converged K-point density.
- **fft** :  The converged FFT grid size.
- **bands**:  The converged  bands value
- **cutoff**:  The converged G-cutoff.
- **ordered_step_output**: Convergence history, with the behaviour of the various 1-D convergence steps.
