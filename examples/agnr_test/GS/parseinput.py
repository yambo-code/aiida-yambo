from __future__ import absolute_import
from __future__ import print_function
import os
from aiida_quantumespresso.tools import pwinputparser
pwinputfile = pwinputparser.PwInputFile(os.path.abspath("./nscf.in"))
print(pwinputfile.namelists, end=' ')
print(dir(pwinputfile), " dir")
struc = pwinputfile.get_structuredata()
#print  struc.store() # 46153
