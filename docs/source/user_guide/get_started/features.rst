.. _2-ref-to-yambo-tutorial:
   
Yambo restart
------------------

The plugin currently support 4 options to start or restart a Yambo calculation:

- **p2y from a NSCF**: this will just run a p2y calculation to create the Yambo SAVE database. It is triggered by using as parent calculation an NSCF run with the quantumespresso.pw plugin and by setting:
::
   
    inputs['settings'] = ParameterData(dict={'initialise': True}) )

- **yambo from a p2y**: triggered simply by using as parent calculation a p2y run with the yambo plugin (as explained above in the option **p2y from a NSCF**)
- **p2y + yambo from a NSCF**: triggered by using as parent calculation an NSCF calculation run with the quantumespresso.pw plugin
- **yambo from a (previous) yambo**: useful for restarts, it is triggered by using as parent calculation a Yambo calculation run with the yambo plugin
