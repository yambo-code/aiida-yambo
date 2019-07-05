from __future__ import absolute_import
import sys

from aiida import load_profile
load_profile()


from aiida.plugins import DataFactory, CalculationFactory, WorkflowFactory

from aiida.orm import RemoteData
from aiida.orm import load_node
from aiida.orm import Code
from aiida.orm import StructureData
from aiida.orm import Float, Str, NumericType, Dict, Int, Bool

from aiida.engine import WorkChain, while_
from aiida.engine import ToContext as ResultToContext ,calcfunction
from aiida.engine import run, submit

from aiida.common import InputValidationError, ValidationError
from aiida.common import AttributeDict
from aiida.common import CalcJobState
from aiida.common import LinkType
from collections import defaultdict

from aiida_yambo.workflows.yambo_utils import generate_pw_input_params
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain
from aiida_quantumespresso.utils.mapping import prepare_process_inputs
from aiida_yambo.calculations.gw import YamboCalculation

KpointsData = DataFactory("array.kpoints")
PwCalculation = CalculationFactory('quantumespresso.pw')
PwBaseWorkChain = WorkflowFactory('quantumespresso.pw.base')

class PwRestartWf(WorkChain):
    """This class is a wrapper for the workflows provided by the aiida-quantumespresso plugin

    This class calls the aiida-quantumespresso PW workflow as a subworkflow with the correct
    parameters, and encodes the logic neccessary to decide whether to do an SCF or an NSCF.
    The subworkflow is assumed to include support for restarting failures from recoverable
    errors such as queue time exhaustion and other similar errors.
    """

    @classmethod
    def define(cls, spec):
        """Workfunction definition

        Provides a thin wrapper around the aiida_quantumespresso PwBaseWorkChain, so yambo workflows
        can be ignorant about the details of running a PW calculation.
        """
        super(PwRestartWf, cls).define(spec)
        #spec.expose_inputs(PwBaseWorkChain, namespace='', exclude=('clean_workdir', 'pw.structure'))
        spec.input("codename", valid_type=Str)
        spec.input("restart_options", valid_type=Dict, required=False)
        spec.input("pseudo_family", valid_type=Str)
        spec.input(
            "calculation_set", valid_type=Dict
        )  # custom_scheduler_commands,  resources,...
        spec.input(
            "calculation_set_nscf", valid_type=Dict,
            required=False)  # custom_scheduler_commands,  resources,...
        spec.input("settings", valid_type=Dict)
        spec.input("settings_nscf", valid_type=Dict, required=False)
        spec.input("structure", valid_type=StructureData)
        spec.input("kpoints", valid_type=KpointsData)
        spec.input("kpoints_nscf", valid_type=KpointsData, required=False)
        spec.input("gamma", valid_type=Bool, default=Bool(0), required=False)
        spec.input("parameters", valid_type=Dict)
        spec.input("parameters_nscf", valid_type=Dict, required=False)
        spec.input("parent_folder", valid_type=RemoteData, required=False)
############################OUTLINE##########################

        spec.outline(cls.pwbegin,
                     while_(cls.pw_should_continue)(cls.pw_continue, ),
                     cls.report_wf)


#############################################################
        spec.output("pw", valid_type=Dict, required=True)

    def pwbegin(self):
        """This function constructs the correct parameters to be passed to the subworkflow, and will also determine the type (SCF vs NSCF)

        This function evaluates the inputs to  the workflow, and if there is a parent calculation passed, check its  type if SCF, then performs
        and NSCF.  If there is no parent calculation, will default to running an SCF calculation, all done through subworkflows from aiida-quantumespresso
        """
        if 'parent_folder' in list(self.inputs.keys()):
            if not isinstance(self.inputs.parent_folder, RemoteData):
                raise InputValidationError(
                    "parent_calc_folder when defined must be of"
                    " type RemoteData")
        try:
            restart_options = self.inputs.restart_options
            try:
                max_restarts = restart_options.get_dict()['max_restarts']
            except KeyError:
                max_restarts = 4
        except AttributeError:
            restart_options = None
            max_restarts = 4
        self.ctx.max_restarts = max_restarts

        parent_folder = None
        inputs = {}
        if 'parent_folder' in list(self.inputs.keys()):
            parameters = self.inputs.parameters.get_dict()  # Will be replaced by parameters_nscf if present and NSCF calc follows.
            parent_folder = self.inputs.parent_folder
            calc = parent_folder.get_incoming().get_node_by_label('remote_folder')
            if calc.inputs.parameters.get_dict()['CONTROL']['calculation'] == 'scf' and calc.is_finished_ok:  # next: nscf
                if 'calculation_set_nscf' not in list(self.inputs.keys()):
                    self.inputs.calculation_set_nscf = self.inputs.calculation_set
                if 'settings_nscf' not in list(self.inputs.keys()):
                    self.inputs.settings_nscf = self.inputs.settings
                if 'kpoints_nscf' not in list(self.inputs.keys()):
                    self.inputs.kpoints_nscf = self.inputs.kpoints
                if 'parameters_nscf' in list(self.inputs.keys()):
                    parameters = self.inputs.parameters_nscf.get_dict()
                if 'force_symmorphic' not in parameters['SYSTEM']:
                    parameters['SYSTEM']['force_symmorphic'] = True
                if 'nbnd' not in parameters['SYSTEM']:
                    try:
                        parameters['SYSTEM']['nbnd'] = calc.outputs.output_parameters.get_dict(
                        )['number_of_electrons'] * 10
                    except KeyError:
                        parameters['SYSTEM']['nbnd'] = int(
                            calc.outputs.output_parameters.
                            get_dict()['number_of_bands'] * 10)  #
                if 'ELECTRONS' not in parameters:
                    parameters['ELECTRONS'] = {}
                    parameters['ELECTRONS']['diagonalization'] = 'davidson'
                    parameters['ELECTRONS']['conv_thr'] = 0.000001
                    parameters['SYSTEM']['nbnd'] = int(
                        parameters['SYSTEM']['nbnd'])
                parameters['CONTROL']['calculation'] = 'nscf'
                self.report("NSCF PARAMS {}".format(parameters))
                self.inputs.parameters_nscf = Dict(
                    dict=parameters
                )  # Added to inputs to allow for RESTART from failed NSCF
                inputs = generate_pw_input_params(
                    self.inputs.structure, self.inputs.codename,
                    self.inputs.pseudo_family, self.inputs.parameters_nscf,
                    self.inputs.calculation_set_nscf, self.inputs.kpoints_nscf,
                    self.inputs.gamma, self.inputs.settings_nscf,
                    parent_folder)
                self.ctx.scf_pk = calc.pk
                self.report(" submitted NSCF {} ".format(calc.pk))

            if calc.inputs.parameters.get_dict(
            )['CONTROL']['calculation'] == 'scf' and not calc.is_finished_ok:  #  starting from failed SCF
                self.report("restarting failed   SCF  {} ".format(calc.pk))
                inputs = generate_pw_input_params(
                    self.inputs.structure, self.inputs.codename,
                    self.inputs.pseudo_family, self.inputs.parameters,
                    self.inputs.calculation_set, self.inputs.kpoints,
                    self.inputs.gamma, self.inputs.settings, parent_folder)

            if calc.inputs.parameters.get_dict(
            )['CONTROL']['calculation'] == 'nscf' and not calc.is_finished_ok:  #  starting from failed NSCF
                self.report("restarting failed NSCF {} ".format(calc.pk))
                inputs = generate_pw_input_params(
                    self.inputs.structure, self.inputs.codename,
                    self.inputs.pseudo_family, self.inputs.parameters_nscf,
                    self.inputs.calculation_set_nscf, self.inputs.kpoints_nscf,
                    self.inputs.gamma, self.inputs.settings_nscf,
                    parent_folder)

            if calc.inputs.parameters.get_dict(
            )['CONTROL']['calculation'] == 'nscf' and calc.is_finished_ok:  #
                self.report(" workflow completed nscf successfully, exiting")
                self.ctx.pw_pks = []
                self.ctx.restart = 0
                self.ctx.success = True
                self.ctx.scf_pk = None
                self.ctx.nscf_pk = calc.pk  # NSCF is done, we should exit
                return
        else:
            self.report("Running from SCF")
            inputs = generate_pw_input_params(
                self.inputs.structure, self.inputs.codename,
                self.inputs.pseudo_family, self.inputs.parameters,
                self.inputs.calculation_set, self.inputs.kpoints,
                self.inputs.gamma, self.inputs.settings, parent_folder)

        future = self.submit(PwBaseWorkChain, **inputs)
        self.ctx.pw_pks = []
        self.ctx.pw_pks.append(future.pk)
        self.ctx.restart = 0
        self.ctx.success = False
        self.ctx.scf_pk = None
        self.ctx.nscf_pk = None
        self.report("submitted subworkflow  {}".format(future.pk))
        return ResultToContext(first_calc=future)

    def pw_should_continue(self):
        """This function runs after each calculation is finished, and decides whether the calculation performed was successfull and which one to do next or restart.

        This function encodes the logic for restarting failed calculations, including deciding if the calculation has failed enough times to warrant exiting the
        workflow. It also decides if the last calculations were successful what calculation to do next, or quit successfully returning computed SCF+NSCF subworkflows.
        """
        if len(self.ctx.pw_pks) == 0:  # we never run a single calculation
            return False

        if self.ctx.success == True:
            return False
        if self.ctx.restart > int(self.ctx.max_restarts):
            return False
        if len(self.ctx.pw_pks) < 1:
            return True
        calc = None
        if len(self.ctx.pw_pks) == 1:
            calc = self.ctx.first_calc.get_outgoing().get_node_by_label('CALL') #outputs.CALL.pk)
        else:
            calc = self.ctx.last_calc.get_outgoing().get_node_by_label('CALL') #outputs.CALL.pk)
        self.report("calc {} ".format(calc))
        if calc.inputs.parameters.get_dict()['CONTROL'][
                'calculation'] == 'scf' and calc.is_finished_ok:
            self.ctx.scf_pk = calc.pk
            self.report(" completed SCF successfully")
            return True
        if calc.is_failed\
            or 'output_parameters' not in calc.outputs  and  self.ctx.restart < 4:
            self.report(" calculation failed  {}, will try restarting".format(
                calc.pk))
            return True
        if calc.inputs.parameters.get_dict()['CONTROL'][
                'calculation'] == 'nscf' and calc.is_finished_ok:
            self.ctx.nscf_pk = calc.pk
            self.ctx.success = True
            self.report("completed NSCF successfully, exiting")
            return False
        if calc.is_failed\
            or 'output_parameters' not in calc.get_outputs_dict()  and  self.ctx.restart >= 4:
            self.ctx.success = False
            self.report(
                "workflow failed to succesfully run any calcultions exiting")
            return False
        self.report("worklfow exiting unsuccessfully ")
        return False

    def pw_continue(self):
        """This function does the actual submissions after the decision has been made whether to continue or not, and will (re)start and SCF (NSCF)

        This function does the actual submission after the first submission done in `self.pwbegin` are complete, and will either restart a failed
        SCF subworkflow or start an NSCF subworkflow from SCF inputs,  or restart a failed NSCF subworkflow
        """
        # restart if neccessary
        calc = None
        if len(self.ctx.pw_pks) == 1:
            calc = load_node(self.ctx.first_calc.get_outgoing().get_node_by_label('CALL').pk)
        else:
            calc = load_node(self.ctx.last_calc.get_outgoing().get_node_by_label('CALL').pk)
        self.report(" continuing from calculation {}".format(calc.pk))
        parameters = calc.inputs.parameters.get_dict()
        scf = ''
        parent_folder = None
        if parameters['CONTROL']['calculation'] == 'scf' and calc.is_finished_ok:
            scf = 'nscf'
            parent_folder = calc.outputs.remote_folder
            self.ctx.scf_pk = calc.pk
        elif parameters['CONTROL']['calculation'] == 'scf' and not calc.is_finished_ok:
            scf = 'scf'  # RESTART
            parent_folder = calc.outputs.remote_folder
            self.ctx.restart += 1  # so we do not end up in an infinite loop
        elif parameters['CONTROL']['calculation'] == 'nscf' and calc.is_finished_ok:
            self.ctx.nscf_pk = calc.pk
            self.ctx.success = True
            self.ctx.restart += 1  # so we do not end up in an infinite loop
            return  # we are finished, ideally we should not need to arrive here, this is also done at self.pw_should_continue
        elif parameters['CONTROL']['calculation'] == 'nscf' and not calc.is_finished_ok:
            scf = 'nscf'  # RESTART
            parent_folder = calc.outputs.remote_folder
            self.ctx.restart += 1  # so we do not end up in an infinite loop
        else:
            self.ctx.success = False
            self.report("workflow in an inconsistent state.")
            return

        if 'parameters_nscf' in list(self.inputs.keys()):
            parameters = self.inputs.parameters_nscf.get_dict()
        if scf == 'nscf':
            if 'calculation_set_nscf' not in list(self.inputs.keys()):
                self.inputs.calculation_set_nscf = self.inputs.calculation_set
            if 'settings_nscf' not in list(self.inputs.keys()):
                self.inputs.settings_nscf = self.inputs.settings
            if 'kpoints_nscf' not in list(self.inputs.keys()):
                self.inputs.kpoints_nscf = self.inputs.kpoints
            if 'force_symmorphic' not in parameters['SYSTEM']:
                parameters['SYSTEM']['force_symmorphic'] = True
            if 'nbnd' not in parameters['SYSTEM']:
                try:
                    parameters['SYSTEM']['nbnd'] = calc.get_outputs_dict(
                    )['output_parameters'].get_dict(
                    )['number_of_electrons'] * 10
                except KeyError:
                    parameters['SYSTEM']['nbnd'] = int(
                        calc.outputs.output_parameters.get_dict()['number_of_bands'] * 10)  #
            parameters['SYSTEM']['nbnd'] = int(parameters['SYSTEM']['nbnd'])
        parameters['CONTROL']['calculation'] = scf

        if 'ELECTRONS' not in parameters:
            parameters['ELECTRONS'] = {}
            parameters['ELECTRONS']['diagonalization'] = 'davidson'
            parameters['ELECTRONS']['conv_thr'] = 0.000001

        self.report(" calculation type:  {} and system {}".format(
            parameters['CONTROL']['calculation'], parameters['SYSTEM']))
        parameters = Dict(dict=parameters)
        if scf == 'nscf':
            inputs = generate_pw_input_params(
                self.inputs.structure, self.inputs.codename,
                self.inputs.pseudo_family, parameters,
                self.inputs.calculation_set_nscf, self.inputs.kpoints_nscf,
                self.inputs.gamma, self.inputs.settings_nscf, parent_folder)
        else:
            inputs = generate_pw_input_params(
                self.inputs.structure, self.inputs.codename,
                self.inputs.pseudo_family, parameters,
                self.inputs.calculation_set, self.inputs.kpoints,
                self.inputs.gamma, self.inputs.settings, parent_folder)
        future = self.submit(PwBaseWorkChain, **inputs)
        self.ctx.pw_pks.append(future.pk)
        self.ctx.restart += 1
        self.report("submitted pw  subworkflow  {}".format(future.pk))
        return ResultToContext(last_calc=future)

    def report_wf(self):
        """Output final quantities

        return information that may be used to figure out
        the status of the calculation.
        """
        self.report("Workflow Complete : scf {}  nscf {} success {}".format(
            self.ctx.scf_pk, self.ctx.nscf_pk, self.ctx.success))

        '''
        if self.ctx.scf_pk:
            scf = self.ctx.scf_pk
            res = Collect_results_scf(Bool(self.ctx.success),Int(scf))
            #self.out("scf_remote_folder",Int(self.ctx.scf_pk))
        '''

        if self.ctx.nscf_pk:
            nscf = self.ctx.nscf_pk
            res = Collect_results_nscf(Bool(self.ctx.success),Int(nscf))
            #self.out("nscf_remote_folder", Int(self.ctx.nscf_pk))

        self.out("pw", res)


@calcfunction
def Collect_results_scf(a,b):
        d = Dict(dict={'success': a, 'scf_pk': b})
        return d

@calcfunction
def Collect_results_nscf(a,b):
        d = Dict(dict={'success': a, 'nscf_pk': b})
        return d


if __name__ == "__main__":
    pass
