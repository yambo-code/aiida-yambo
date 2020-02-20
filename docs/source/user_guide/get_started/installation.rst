
Getting the plugin
------------------

The plugin can be installed using pip

::

    pip install aiida-yambo

or downloaded from github

::

    git clone https://github.com/yambo-code/yambo-aiida.git
    cd aiida_yambo
    pip install -e aiida-yambo



Setup Yambo on AiiDA
---------------------

In order to set up the p2y and yambo executables as an AiiDA codes, use the name ``yambo.yambo`` as the plugin name

::

    $ verdi code setup
    At any prompt, type ? to get some help.
    ---------------------------------------
    => Label: yambo_codename
    => Description: YAMBO MBPT code
    => Local: False
    => Default input plugin: yambo.yambo
    => Remote computer name: marconi
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
