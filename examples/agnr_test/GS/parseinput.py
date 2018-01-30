import os
from aiida_quantumespresso.tools import pwinputparser
pwinputfile = pwinputparser.PwInputFile(os.path.abspath("./nscf.in"))
print pwinputfile.namelists, 
print dir(pwinputfile) , " dir"
struc =  pwinputfile.get_structuredata()
#print  struc.store() # 46153
