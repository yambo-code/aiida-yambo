(protocols)=

# Protocols

Protocols are an efficient way to perform automatic inputs creation, starting only from the structure and few
other parameters. The aiida-quantumespresso plugin provides a set of tested protocols, based on the compromise
between speed and accuracy that we may want to achieve. In MBPT there are no such protocols, but anyway an automatic
input creation can be useful for non-expert users, but also for expert users who don't want to loose to much time
in the input creation step. So, we decided to provide three protocols, 'fast', 'moderate' and 'precise', which provides
automatic GW inputs based on heuristics and user experience. 

Overrides can be provided to re-set default inputs in examples of the aiida-yambo-wannier90 plugin. 
Just run, for example:

```bash
    ./example_03.py
```

Example names are the same of the one provided in the aiida-yambo-wannier90 plugin, and detailed explanations are provided in 
the corresponding documentation.