# -*- coding: utf-8 -*-
"""
Plugin to create a Yambo input file.
"""
from __future__ import absolute_import
import os
from aiida.engine import CalcJob
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import CalcJobState
from aiida_quantumespresso.calculations import _lowercase_dict, _uppercase_dict
from aiida.common.exceptions import UniquenessError, InputValidationError
from aiida.common.utils import classproperty
from aiida.orm.nodes import Dict
from aiida.orm.nodes import RemoteData
from aiida.plugins import DataFactory, CalculationFactory
from aiida.orm import Code
from aiida.common import AIIDA_LOGGER
from aiida.common import LinkType
import six
PwCalculation = CalculationFactory('quantumespresso.pw')

__authors__ = " Gianluca Prandini (gianluca.prandini@epfl.ch)," \
              " Antimo Marrazzo (antimo.marrazzo@epfl.ch)," \
              " Michael Atambo (michaelontita.atambo@unimore.it)."


class YamboCalculation(CalcJob):
    """
    AiiDA plugin for the Yambo code.
    For more information, refer to http://www.yambo-code.org/
    https://github.com/yambo-code/yambo-aiida and http://aiida-yambo.readthedocs.io/en/latest/
    """

    # Default input and output files
    _DEFAULT_INPUT_FILE = 'aiida.in'
    _DEFAULT_OUTPUT_FILE = 'aiida.out'

    @classmethod
    def define(cls,spec):
        super(YamboCalculation, cls).define(spec)
        spec.input('metadata.options.input_filename', valid_type=six.string_types, default=cls._DEFAULT_INPUT_FILE)
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._DEFAULT_OUTPUT_FILE)

       # Default output parser provided by AiiDA
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default='yambo.yambo')
 
       # self._SCRATCH_FOLDER = 'SAVE'
        spec.input('metadata.options.scratch_folder', valid_type=six.string_types, default='SAVE')
   

        spec.input('metadata.options.logostring', valid_type=six.string_types, default="""
#                                                           
# Y88b    /   e           e    e      888~~\    ,88~-_      
#  Y88b  /   d8b         d8b  d8b     888   |  d888   \     
#   Y88b/   /Y88b       d888bdY88b    888 _/  88888    |    
#    Y8Y   /  Y88b     / Y88Y Y888b   888  \  88888    |    
#     Y   /____Y88b   /   YY   Y888b  888   |  Y888   /     
#    /   /      Y88b /          Y888b 888__/    `88_-~      
#                                                           
#             AIIDA input plugin.  YAMBO 4.x compatible
#               http://www.yambo-code.org                   
#
"""
)

    @classmethod
    def define(cls,spec):
        super(YamboCalculation,cls).define(spec)
        
        spec.input_namespace('settings',valid_type=Dict,
                help='Use an additional node for special settings',dynamic=True)
        spec.input_namespace('parameters',valid_type=Dict,
                help='Use a node that specifies the input parameters',dynamic=True)
        spec.input_namespace('parent_folder',valid_type=RemoteData,
                help='Use a remote folder as parent folder (for "restarts and similar")',dynamic=True)
        spec.input_namespace('preprocessing_code',valid_type=Code,
                help='Use a preprocessing code for starting yambo',dynamic=True)
        spec.input_namespace('precode_parameters',valid_type=Dict,
                help='Use a node that specifies the input parameters for the yambo precode',dynamic=True)
        spec.input_namespace('main_code',valid_type=Code,
                help='Use a main code for yambo calculation',dynamic=True)

    def prepare_for_submission(self, folder):

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []

        # Settings can be undefined, and defaults to an empty dictionary.
        # They will be used for any input that doen't fit elsewhere.
        
        settings = self.inputs.settings

        initialise = settings.pop('INITIALISE', None)
        if initialise is not None:
            if not isinstance(initialise, bool):
                raise InputValidationError("INITIALISE must be " " a boolean")
        
        parameters = self.inputs.parameters

        if not initialise:
            if not isinstance(parameters, Dict):
                raise InputValidationError(
                    "parameters is not of type Dict")

        parent_calc_folder = self.inputs.parent_folder

        main_code = self.inputs.main_code

        preproc_code = self.inputs.preprocessing_code

        parent_calc = parent_calc_folder.get_inputs_dict(
            link_type=LinkType.CREATE)['remote_folder']
        yambo_parent = isinstance(parent_calc, YamboCalculation)

        # flags for yambo interfaces
        precode_param_dict = self.inputs.precode_parameters

        # check the precode parameters given in input
        input_cmdline = settings.pop('CMDLINE', None)
        import re
        precode_params_list = []
        pattern = re.compile(r"(^\-)([a-zA-Z])")
        for key, value in six.iteritems(precode_param_dict):
            if re.search(pattern, key) is not None:
                if key == '-O' or key == '-H' or key == '-h' or key == '-F':
                    raise InputValidationError(
                        "Precode flag {} is not allowed".format(str(key)))
                else:
                    if precode_param_dict[key] is True:
                        precode_params_list.append(str(key))
                    elif precode_param_dict[key] is False:
                        pass
                    else:
                        precode_params_list.append('{}'.format(str(key)))
                        precode_params_list.append('{}'.format(str(value)))
            else:
                raise InputValidationError(
                    "Wrong format of precode_parameters")
        # Adding manual cmdline input (e.g. for DB fragmentation)
        if input_cmdline is not None:
            precode_params_list = precode_params_list + input_cmdline

        # TODO: check that remote data must be on the same computer

        ##############################
        # END OF INITIAL INPUT CHECK #
        ##############################

        if not initialise:
            ###################################################
            # Prepare yambo input file
            ###################################################

            params_dict = parameters.get_dict()

            # extract boolean keys
            boolean_dict = {
                k: v
                for k, v in six.iteritems(params_dict) if isinstance(v, bool)
            }
            params_dict = {
                k: v
                for k, v in six.iteritems(params_dict)
                if k not in list(boolean_dict.keys())
            }

            # reorganize the dictionary and create a list of dictionaries with key, value and units
            parameters_list = []
            for k, v in six.iteritems(params_dict):

                if "_units" in k:
                    continue

                units_key = "{}_units".format(k)
                try:
                    units = params_dict[units_key]
                except KeyError:
                    units = None

                this_dict = {}
                this_dict['key'] = k
                this_dict['value'] = v
                this_dict['units'] = units

                parameters_list.append(this_dict)

            input_filename = tempfolder.get_abs_path(self._INPUT_FILE_NAME)

            with open(input_filename, 'w') as infile:
                infile.write(self._LOGOSTRING)

                for k, v in six.iteritems(boolean_dict):
                    if v:
                        infile.write("{}\n".format(k))

                for this_dict in parameters_list:
                    key = this_dict['key']
                    value = this_dict['value']
                    units = this_dict['units']

                    if isinstance(value, (tuple, list)):
                        # write the input flags for the Drude term and for the parallelization options of vers. 4
                        # (it can be implemented in a better way)
                        if key.startswith('DrudeW'):
                            value_string = " ( " + ",".join(
                                [str(_) for _ in value]) + " )"
                            the_string = "{} = {}".format(key, value_string)
                            the_string += " {}".format(units)
                            infile.write(the_string + "\n")
                            continue

                        if key == 'SE_CPU':
                            value_string = " \" " + " ".join(
                                [str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write("SE_ROLEs = \" q qp b  \" " + "\n")
                            infile.write(the_string + "\n")
                            continue

                        if key == 'X_all_q_CPU':
                            value_string = " \" " + " ".join(
                                [str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write("X_all_q_ROLEs = \" q k c v  \" " +
                                         "\n")
                            infile.write(the_string + "\n")
                            continue

                        if key == 'X_finite_q_CPU':
                            value_string = " \" " + " ".join(
                                [str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write("X_finite_q_ROLEs = \" q k c v  \" " +
                                         "\n")
                            infile.write(the_string + "\n")
                            continue

                        if key == 'X_q_0_CPU':
                            value_string = " \" " + " ".join(
                                [str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write("X_q_0_ROLEs = \" k c v  \" " + "\n")
                            infile.write(the_string + "\n")
                            continue

                        if key == 'QPkrange' or key == 'QPerange':
                            value_string = ''
                            for v in value:
                                value_string += " | ".join([str(_) for _ in v
                                                            ]) + " |\n"
                            the_string = "% {}\n {}".format(key, value_string)
                            the_string += "%"
                            infile.write(the_string + "\n")
                            continue

                        value_string = " | ".join([str(_)
                                                   for _ in value]) + " |"
                        the_string = "% {}\n {}".format(key, value_string)
                        if units is not None:
                            the_string += " {}".format(units)
                        the_string += "\n%"

                    else:
                        the_value = '"{}"'.format(value) if isinstance(
                            value, six.string_types) else '{}'.format(value)
                        the_string = "{} = {}".format(key, the_value)
                        if units is not None:
                            the_string += " {}".format(units)

                    infile.write(the_string + "\n")

        ############################################
        # set copy of the parent calculation
        ############################################

        parent_calcs = parent_calc_folder.get_inputs(link_type=LinkType.CREATE)
        if len(parent_calcs) > 1:
            raise UniquenessError(
                "More than one parent totalenergy calculation"
                "has been found for parent_calc_folder {}".format(
                    parent_calc_folder))
        if len(parent_calcs) == 0:
            raise InputValidationError(
                "No parent calculation associated with parent_folder {}".
                format(parent_calc_folder))
        parent_calc = parent_calcs[0]

        if yambo_parent:
            try:
                parent_settings = _uppercase_dict(
                    parent_calc.inp.settings.get_dict(),
                    dict_name='parent settings')
                parent_initialise = parent_settings['INITIALISE']
            except KeyError:
                parent_initialise = False

        if yambo_parent:
            remote_copy_list.append((parent_calc_folder.computer.uuid,
                                     os.path.join(
                                         parent_calc_folder.get_remote_path(),
                                         "SAVE"), "SAVE/"))
            if not parent_initialise:
                cancopy = False
                if parent_calc.get_state() == calc_states.FINISHED:
                    cancopy = True
                if 'yambo_wrote' in list(
                        parent_calc.get_outputs_dict()['output_parameters'].
                        get_dict().keys()):
                    if parent_calc.get_outputs_dict(
                    )['output_parameters'].get_dict()['yambo_wrote'] == True:
                        cancopy = True
                    if parent_calc.get_outputs_dict(
                    )['output_parameters'].get_dict()['yambo_wrote'] == False:
                        cancopy = False
                if cancopy:
                    remote_copy_list.append(
                        (parent_calc_folder.computer.uuid,
                         os.path.join(parent_calc_folder.get_remote_path(),
                                      "aiida"), "aiida/"))
        else:
            remote_copy_list.append(
                (parent_calc_folder.computer.uuid,
                 os.path.join(parent_calc_folder.get_remote_path(),
                              PwCalculation._OUTPUT_SUBFOLDER,
                              "{}.save".format(parent_calc._PREFIX), "*"),
                 "."))
        ############################################
        # set Calcinfo
        ############################################

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid

        calcinfo.local_copy_list = []
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = []  # remote_symlink_list

        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append('r*')
        calcinfo.retrieve_list.append('l*')
        calcinfo.retrieve_list.append('o*')
        calcinfo.retrieve_list.append('LOG/l-*_CPU_1')
        extra_retrieved = settings_dict.pop(
            'ADDITIONAL_RETRIEVE_LIST',
            ['aiida/ndb.QP', 'aiida/ndb.HF_and_locXC'])
        for extra in extra_retrieved:
            calcinfo.retrieve_list.append(extra)

        from aiida.common.datastructures import code_run_modes, CodeInfo

        # c1 = interface dft codes and yambo (ex. p2y or a2y)
        c1 = CodeInfo()
        c1.withmpi = True
        c1.cmdline_params = precode_params_list

        # c2 = yambo initialization
        c2 = CodeInfo()
        c2.withmpi = True
        c2.cmdline_params = []
        c2.code_uuid = main_code.uuid

        # if the parent calculation is a yambo calculation skip the interface (c1) and the initialization (c2)
        if yambo_parent:
            c1 = None
            if not parent_initialise:
                c2 = None
        else:
            c1.cmdline_params = precode_params_list
            c1.code_uuid = preproc_code.uuid

        # c3 = yambo calculation
        c3 = CodeInfo()
        c3.withmpi = self.get_withmpi()
        c3.cmdline_params = [
            "-F", self._INPUT_FILE_NAME, '-J', self._OUTPUT_FILE_NAME
        ]
        c3.code_uuid = main_code.uuid

        if initialise:
            c2 = None
            c3 = None

        #calcinfo.codes_info = [c1, c2, c3] if not yambo_parent else [c3]
        if yambo_parent:
            if not parent_initialise:
                calcinfo.codes_info = [c3]
            else:
                calcinfo.codes_info = [c2, c3]
        elif initialise:
            calcinfo.codes_info = [c1]
        else:
            calcinfo.codes_info = [c1, c2, c3]

        calcinfo.codes_run_mode = code_run_modes.SERIAL

        if settings:
            raise InputValidationError(
                "The following keys have been found in "
                "the settings input node, but were not understood: {}".format(
                    ",".join(list(settings.keys()))))

        return calcinfo

    def _check_valid_parent(self, calc):
        """
        Check that calc is a valid parent for a YamboCalculation.
        It can be a PwCalculation or a YamboCalculation.
        """

        try:
            if ((not isinstance(calc, PwCalculation))
                    and (not isinstance(calc, YamboCalculation))):
                raise ValueError(
                    "Parent calculation must be a PwCalculation or a YamboCalculation"
                )

        except ImportError:
            if ((not isinstance(calc, PwCalculation))
                    and (not isinstance(calc, YamboCalculation))):
                raise ValueError(
                    "Parent calculation must be a PwCalculation or a YamboCalculation"
                )

    def use_parent_calculation(self, calc):
        """
        Set the parent calculation of Yambo, 
        from which it will inherit the outputsubfolder.
        The link will be created from parent RemoteData to YamboCalculation 
        """
        from aiida.common.exceptions import NotExistent

        self._check_valid_parent(calc)

        remotedatas = calc.get_outputs(node_type=RemoteData)
        if not remotedatas:
            raise NotExistent("No output remotedata found in " "the parent")
        if len(remotedatas) != 1:
            raise UniquenessError("More than one output remotedata found in "
                                  "the parent")
        remotedata = remotedatas[0]

        self._set_parent_remotedata(remotedata)

    def _set_parent_remotedata(self, remotedata):
        """
        Used to set a parent remotefolder in the start of Yambo.
        """
        if not isinstance(remotedata, RemoteData):
            raise ValueError('remotedata must be a RemoteData')

        # complain if another remotedata is already found
        input_remote = self.get_inputs(node_type=RemoteData)
        if input_remote:
            raise ValidationError("Cannot set several parent calculation to a "
                                  "Yambo calculation")

        self.use_parent_folder(remotedata)
