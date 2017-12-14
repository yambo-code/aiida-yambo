.. _2-ref-to-yambo-tutorial:

Yambo G0W0 Tutorial
====================

.. toctree::
   :maxdepth: 2
   
Getting the plugin
------------------
The plugin can be downloaded from the repository or installed via pip

::

    git clone https://github.com/yambo-code/yambo-aiida.git   aiida_yambo
    cd aiida_yambo
    python setup.py install

Later the plugin will be available on PyPi, and will be obtained via, 

::

    pip install aiida-yambo


Setup Yambo Code
----------------

When setting up  yambo code on aiida use the name ``yambo.yambo`` as the plugin to
use for that code.

::

    $ verdi code setup 
    At any prompt, type ? to get some help.
    ---------------------------------------
    => Label: yambo_example
    => Description: YAMBO MBPT code
    => Local: False
    => Default input plugin: yambo.yambo
    => Remote computer name: marconi
    => Remote absolute path: /s3_home/hpc/applications/yambo-src/bin/yambo
    => Text to prepend to each command execution
    FOR INSTANCE, MODULES TO BE LOADED FOR THIS CODE: 
       # This is a multiline input, press CTRL+D on a
       # empty line when you finish
       # ------------------------------------------
       # End of old input. You can keep adding     
       # lines, or press CTRL+D to store this value
       # ------------------------------------------
    => Text to append to each command execution: 
       # This is a multiline input, press CTRL+D on a
       # empty line when you finish
       # ------------------------------------------
       # End of old input. You can keep adding     
       # lines, or press CTRL+D to store this value
       # ------------------------------------------
    Code 'yambo_example' successfully stored in DB.
    pk: 38316, uuid: 24f75bca-2975-49a5-af2f-97a917bd6ee4
