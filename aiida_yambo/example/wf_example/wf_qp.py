import sys
from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.orm import load_node
from aiida.orm.data.upf import get_pseudos_from_structure
from aiida.workflows2.defaults import registry
from collections import defaultdict
from aiida.orm.utils import DataFactory
from aiida.workflows2.db_types import Float, Str, NumericType, SimpleData
from aiida.orm.code import Code
from aiida.orm.data.structure import StructureData
from aiida.workflows2.run import run
from aiida.workflows2.fragmented_wf import FragmentedWorkfunction, \
    ResultToContext, while_
from aiida.workflows2.wf import wf
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation
from aiida.orm.calculation.job.yambo  import YamboCalculation

ParameterData = DataFactory("parameter")
KpointsData = DataFactory("array.kpoints")
PwProcess = PwCalculation.process()
YamboProcess = YamboCalculation.process()

def get_structure():
    StructureData = DataFactory('structure')
    cell=[[   15.8753100000,    0.0000000000,    0.0000000000],
        [0.0000000000 , 15.8753100000 , 0.0000000000],
        [0.0000000000  , 0.0000000000  , 2.4696584760]]
    s = StructureData(cell=cell)
    s.append_atom(position=(0.0000000000, 0.0000000000, -0.5857830640), symbols='C')
    s.append_atom(position=(0.6483409550, 0.0000000000, 0.5857863990), symbols='C')
    s.append_atom(position=(-1.0769905460, 0.0000000000, -0.5902956470), symbols='H')
    s.append_atom(position=(1.7253315010, 0.0000000000, 0.5902989820), symbols='H')
    s.store()
    return s 

def get_parameter_data(typ):
    if typ == 'scf':
        parameters = ParameterData(dict={
                  'CONTROL': {
                      'calculation': 'scf',
                      'restart_mode': 'from_scratch',
                      'wf_collect': True,
                      'tprnfor': True,
                      'verbosity' :'high',
                      },
                  'SYSTEM': {
                      'ecutwfc': 45.,
                      'nspin': 2,
                      'starting_magnetization(1)': 0,
                      'occupations':'smearing',
                      'degauss': 0.3
                      },
                  'ELECTRONS': {
                      'conv_thr': 1.e-8,
                      'electron_maxstep ': 50,
                      'mixing_mode': 'plain',
                      'mixing_beta' : 0.4,
                      }})
    else:
        parameters = ParameterData(dict={
                  'CONTROL': {
                      'calculation': 'nscf',
                      'restart_mode': 'from_scratch',
                      'wf_collect': True,
                      'verbosity' :'high',
                      },
                  'SYSTEM': {
                      'ecutwfc': 45,
                      'force_symmorphic': True,
                      'nbnd':  50,
                      'nspin': 2,
                      'starting_magnetization(1)': 0,
                      'smearing': 'gaussian',
                      'occupations':'smearing',
                      'degauss': 0.3
                      },
                  'ELECTRONS': {
                      'conv_thr': 1.e-8,
                      'electron_maxstep ': 50,
                      'mixing_mode': 'plain',
                      'mixing_beta' : 0.4
                      }})
    return parameters

def get_yamboparameter_data():
    parameters = ParameterData(dict={'ppa': True,
                                 'gw0': True,
                                 'rim_cut': True,
                                 'HF_and_locXC': True,
                                 'em1d': True,
                                 'X_all_q_CPU': "1 2 8 2",
                                 'X_all_q_ROLEs': "q k c v",
                                 'X_all_q_nCPU_invert':0,
                                 'X_Threads':  1 ,
                                 'DIP_Threads': 1 ,
                                 'SE_CPU': "1 4 8",
                                 'SE_ROLEs': "q qp b",
                                 'SE_Threads':  1,
                                 'RandQpts': 0,
                                 'RandGvec': 1,
                                 'RandGvec_units': 'RL',
                                 'CUTGeo': "none",
                                 'CUTBox': (0.0,0.0,0.0),
                                 'CUTRadius': 0.0,
                                 'CUTCylLen': 0.0,
                                 'EXXRLvcs': 170943,
                                 'EXXRLvcs_units': 'RL',
                                 'BndsRnXp': (1,50),
                                 'NGsBlkXp': 3,
                                 'NGsBlkXp_units': 'Ry',
                                 'LongDrXp': (1,0,0),
                                 'PPAPntXp': 20,
                                 'PPAPntXp_units': 'eV',
                                 'GbndRnge': (1,50),
                                 'GDamping': 0.1,
                                 'GDamping_units': 'eV',
                                 'dScStep': 0.1,
                                 'dScStep_units': 'eV',
                                 'GTermKind': "none",
                                 'DysSolver': "n",
                                  "Chimod": "",
                                 'QPkrange': [(1,1,5,6),(16,16,5,6)],
                                 }
                           )
    return parameters

def get_kpoints():
    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([1,1,30])
    return kpoints

def get_options():
    max_wallclock_seconds = 240*60  # 3 hrs 
    resources = {"num_machines": 2}
  #  queue_name = "s3par8cv3" 
    return resources, max_wallclock_seconds, queue_name

def get_pseudo(structure, pseudo_family):
    kind_pseudo_dict = get_pseudos_from_structure(structure, pseudo_family)
    pseudo_dict = {}
    pseudo_species = defaultdict(list)
    for kindname, pseudo in kind_pseudo_dict.iteritems():
        pseudo_dict[pseudo.pk] = pseudo
        pseudo_species[pseudo.pk].append(kindname)
    pseudos = {}
    for pseudo_pk in pseudo_dict:
        pseudo = pseudo_dict[pseudo_pk]
        kinds = pseudo_species[pseudo_pk]
        for kind in kinds:
            pseudos[kind] = pseudo
    return pseudos

def generate_scf_input_params(structure, codename, pseudo_family):
    inputs = PwCalculation.process().get_inputs_template()
    inputs.structure = structure 
    inputs.code = Code.get_from_string(codename.value)
    inputs._options.resources,\
        inputs._options.max_wallclock_seconds,\
     #   inputs._options.queue_name = get_options()
    inputs.kpoints = get_kpoints()
    inputs.parameters = get_parameter_data('scf')
    inputs.pseudo = get_pseudo(structure, str(pseudo_family))
    return  inputs 

def generate_nscf_input_params(structure, codename, pseudo_family,parent_folder):
    inputs = PwCalculation.process().get_inputs_template()
    inputs.structure = structure
    inputs.code = Code.get_from_string(codename.value)
    inputs._options.resources,\
        inputs._options.max_wallclock_seconds,\
       # inputs._options.queue_name = get_options()
    inputs.kpoints = get_kpoints()
    inputs.parameters = get_parameter_data('nscf')
    inputs.parent_folder = parent_folder
    inputs.pseudo = get_pseudo(structure, str(pseudo_family))
    return  inputs

def generate_yambo_input_params(structure, precodename,yambocodename, pseudo_family,parent_folder):
    inputs = YamboCalculation.process().get_inputs_template()
    inputs.preprocessing_code = Code.get_from_string(precodename.value)
    inputs.code = Code.get_from_string(yambocodename.value)
    inputs._options.resources,\
        inputs._options.max_wallclock_seconds,\
       # inputs._options.queue_name = get_options()
    inputs.parameters = get_yamboparameter_data()
    inputs.parent_folder = parent_folder
    inputs.settings =  ParameterData(dict={"ADDITIONAL_RETRIEVE_LIST":[
                  'r-*','o-*','l-*','LOG/l-*_CPU_1','aiida/ndb.QP','aiida/ndb.HF_and_locXC']})
    return  inputs

class QPCalculation(FragmentedWorkfunction):
    """
    Converge to minimum using Newton's algorithm on the first derivative of the energy (minus the pressure).
    """

    @classmethod
    def _define(cls, spec):
        """
        Workfunction definition
        """
        spec.input("structure", valid_type=StructureData)
        spec.input("pwcode", valid_type=SimpleData)
        spec.input("precode", valid_type=SimpleData)
        spec.input("yambocode", valid_type=SimpleData)
        spec.input("pseudo_family", valid_type=SimpleData)
        spec.outline(
            cls.scf,
            cls.nscf,
            cls.yambo,
            cls.report
        )
        spec.dynamic_output()

    def scf(self, ctx):
        """
        Launch an scf calculation, 
        """
        inputs = generate_scf_input_params(
            self.inputs.structure, self.inputs.pwcode, self.inputs.pseudo_family)

        future = self.submit(PwProcess, inputs)
        ctx.scf_pk = future.pid
        return ResultToContext(scf=future)

    def nscf(self, ctx):
        """
        Run an nscf calculation after the scf is done
        """
        parentcalc = load_node(ctx.scf_pk)
        s = parentcalc.inp.structure
        parent_folder = parentcalc.out.remote_folder
        structure =  s 
        inputs = generate_nscf_input_params(
            structure, self.inputs.pwcode,
            self.inputs.pseudo_family, parent_folder)
        # Run PW
        future = self.submit(PwProcess, inputs)
        ctx.nscf_pk = future.pid
        return ResultToContext(nscf=future)

    def yambo(self, ctx):
        """
        Run the  pw-> yambo conversion, init and yambo run
        """
        parentcalc = load_node(ctx.nscf_pk)
        s = parentcalc.inp.structure
        parent_folder = parentcalc.out.remote_folder

        inputs = generate_yambo_input_params(
            structure, self.inputs.precode,self.inputs.yambocode,
            self.inputs.pseudo_family,parent_folder )

        # Run PW
        future = self.submit(YamboProcess, inputs)
        ctx.yambo_pk =  future.pid
        return ResultToContext(yambo=future)

    def report(self, ctx):
        """
        Output final quantities
        """
        from aiida.orm import DataFactory
        self.out("steps", DataFactory('parameter')(dict={
            'scf': ctx.scf['output_parameters'],
            'nscf': ctx.nscf['output_parameters'],
            }))

if __name__ == "__main__":
    import argparse
    # verdi run wf_qp.py  --pseudo "CHtest" --pwcode "pw@hyd" --precode "p2y@hyd" --yambocode "yambo@hyd"
    parser = argparse.ArgumentParser(description='GW QP calculation.')
    parser.add_argument('--pseudo', type=str, dest='pseudo', required=True,
                        help='The pseudopotential family')
    parser.add_argument('--pwcode', type=str, dest='pwcode', required=True,
                        help='The codename to use')
    parser.add_argument('--precode', type=str, dest='precode', required=True,
                        help='The codename to use')
    parser.add_argument('--yambocode', type=str, dest='yambocode', required=True,
                        help='The codename to use')

    structure = get_structure()

    args = parser.parse_args()
    wf_results = run(QPCalculation, structure=structure,
                     pwcode=Str(args.pwcode),precode=Str(args.precode),
                     yambocode=Str(args.yambocode), pseudo_family=Str(args.pseudo),
                     )
    print "Workflow results:"
    print wf_results
