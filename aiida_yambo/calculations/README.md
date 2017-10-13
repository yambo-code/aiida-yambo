# Yambo plugin for AiiDA #

IMPORTANT REMARKS

-A plugin is made of two files, one (called input or job) manages the input file and the other (parser) handles the parsing of the output files.

-Here me make two repositories for the two parts of the plugin (input and parser). Essentially, you will have two yambo folders with different paths (one where we place the input plugin and the other for the parser).

-The main plugin is in the file 
```__init__.py```

-Additional files (e.g. input examples) should be in the resources folder.

-You should commit ONLY within the yambo folder

-Here you find the instructions to get the code

```
#!bash
git clone https://bitbucket.org/aiida_team/aiida_core.git aiida  #Public repository  of aiida_core (MIT license)
git checkout develop   #Most recent develop branch
cd aiida/aiida/orm/calculation/job # Input plugin folder
git clone https://username@bitbucket.org/prandini/yambo_input.git yambo #The folder HAS to be called yambo
cd yambo
#Now you do the same for the parser plugin
cd aiida/aiida/parsers/plugins # Parser plugin folder
git clone https://username@bitbucket.org/prandini/yambo_parser.git yambo #The folder HAS to be called yambo
cd yambo

```