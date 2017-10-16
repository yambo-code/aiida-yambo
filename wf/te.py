from aiida.parsers.plugins.yambo.ext_dep.yambofile  import  YamboFile
from aiida.parsers.plugins.yambo.ext_dep.yambofolder  import  YamboFolder
calc = load_node(2942)
outf = calc.get_retrieved_node()
outf.get_abs_path()
results = YamboFolder(outf.get_abs_path())
