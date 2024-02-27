(installation)=

# Installation

The plugin can be downloaded from the official github repository

```bash
$ git clone https://github.com/yambo-code/yambo-aiida.git
$ cd aiida_yambo
$ pip install .
```
or installed from the Python Package Index (PyPI) using pip

```bash
$ pip install aiida-yambo
```

in order to successfully install the plugin, follow the related [AiiDA documentation](http://aiida-core.readthedocs.io/en/latest/index.html).


## Setup Yambo on AiiDA

In order to set up the p2y and yambo executables as an AiiDA codes, use the name ``yambo.yambo`` as the plugin name

```bash
$ verdi code setup
At any prompt, type ? to get some help.
---------------------------------------
=> Label: yambo_codename
=> Description: YAMBO MBPT code
=> Local: False
=> Default input plugin: yambo.yambo
=> Remote computer name: @cluster
=> Remote absolute path: /your_path_to_yambo
=> Text to prepend to each command execution
FOR INSTANCE, MODULES TO BE LOADED FOR THIS CODE:
    # This is a multiline input, press CTRL+D on a
    # empty line when you finish
    # ------------------------------------------
    # End of old input. You can keep adding
    # lines, or press CTRL+D to store this value
    # ------------------------------------------
module load your_module_name
=> Text to append to each command execution:
    # This is a multiline input, press CTRL+D on a
    # empty line when you finish
    # ------------------------------------------
    # End of old input. You can keep adding
    # lines, or press CTRL+D to store this value
    # ------------------------------------------
Code 'yambo_codename' successfully stored in DB.
pk: 38316, uuid: 24f75bca-2975-49a5-af2f-97a917bd6ee4
```

To setup a code (as well as a computer) in AiiDA there is also the possibility to define a YAML-format file (HERE REF To that part of the docs):

```bash 
---
label: "yambo-5.1"
description: "yambo v5.1"
input_plugin: "yambo.yambo"
on_computer: true
remote_abs_path: "path_to_yambo_folder/bin/yambo"
computer: "@cluster"
prepend_text: |
    ''module load ...
    export OMP_NUM_THREADS = ''

append_text: ""
```

To store the code, just type ``verdi code setup --config file.yml``.

Tip: for SLURM schedulers we suggest to set, in the prepend text of the computer (so, for all codes) 
or of the code (if you need case-sensitive settings) the following command:

```bash
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK 
```

This will automatically set the right number of threads. For PBS/Torque, you need to set the 
environment variable `OMP_NUM_THREADS `by using the prepend_text key in the `options` python dictionary 
of the calculation.  
