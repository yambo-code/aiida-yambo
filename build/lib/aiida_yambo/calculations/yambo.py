# -*- coding: utf-8 -*-
"""
Plugin to create a Yambo input file and run a calculation with the yambo executable.
"""
from __future__ import absolute_import
import os
import six

from aiida.engine import CalcJob

from aiida_quantumespresso.calculations import _lowercase_dict, _uppercase_dict

from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import CalcJobState
from aiida.common.exceptions import UniquenessError, InputValidationError, ValidationError
from aiida.common.utils import classproperty

from aiida.orm import Code
from aiida.orm.nodes import Dict
from aiida.orm.nodes import RemoteData, BandsData, ArrayData

from aiida.plugins import DataFactory, CalculationFactory

from aiida.common import AIIDA_LOGGER
from aiida.common import LinkType

from aiida_yambo.utils.common_helpers import * 

PwCalculation = CalculationFactory('quantumespresso.pw')

__authors__ = " Miki Bonacci (miki.bonacci@unimore.it)," \
              " Gianluca Prandini (gianluca.prandini@epfl.ch)," \
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


        spec.input('settings',valid_type=Dict,
                help='Use an additional node for special settings')
        spec.input('parameters',valid_type=Dict,
                help='Use a node that specifies the input parameters')
        spec.input('parent_folder',valid_type=RemoteData,
                help='Use a remote folder as parent folder (for "restarts and similar"')
        spec.input('preprocessing_code',valid_type=Code,
                help='Use a preprocessing code for starting yambo',required=False)
        spec.input('precode_parameters',valid_type=Dict,
                help='Use a node that specifies the input parameters for the yambo precode',required=False)
        spec.input('code',valid_type=Code,
                help='Use a main code for yambo calculation')

        spec.exit_code(500, 'ERROR_NO_RETRIEVED_FOLDER',
                message='The retrieved folder data node could not be accessed.')
        spec.exit_code(501, 'WALLTIME_ERROR',
                message='time exceeded the max walltime')
        spec.exit_code(502, 'NO_SUCCESS',
                message='failed calculation for some reason: could be a low number of conduction bands')
        spec.exit_code(503, 'PARSER_ANOMALY',
                message='Unexpected behavior of YamboFolder')
        spec.exit_code(504, 'PARA_ERROR',
                message='parallelization error')
        spec.exit_code(505, 'MEMORY_ERROR',
                message='general memory error')
        spec.exit_code(506, 'X_par_MEMORY_ERROR',
                message='x_par allocation memory error')


        #outputs definition:

        spec.output('output_parameters', valid_type=Dict,
                required=True, help='returns the output parameters')
        spec.output('array_alpha', valid_type=ArrayData,
                required=False, help='returns the alpha array')
        spec.output('array_alpha_bands', valid_type=ArrayData,
                required=False, help='returns the alpha array bands')
        spec.output('array_alpha_array', valid_type=ArrayData,
                required=False, help='returns the alpha array')
        spec.output('bands_quasiparticle', valid_type=BandsData,
                required=False, help='returns the quasiparticle band structure')
        spec.output('array_qp', valid_type=ArrayData,
                required=False, help='returns the quasiparticle array band structure')
        spec.output('array_eels', valid_type=ArrayData,
                required=False, help='returns the eels array')
        spec.output('array_eps', valid_type=ArrayData,
                required=False, help='returns the eps array')
        spec.output('array_ndb', valid_type=ArrayData,
                required=False, help='returns the array for ndb')
        spec.output('array_ndb_QP', valid_type=ArrayData,
                required=False, help='returns the array for ndbQP')
        spec.output('array_ndb_HFlocXC', valid_type=ArrayData,
                required=False, help='returns the array ndb for HFlocXC')
        spec.output('system_info', valid_type=Dict,
                required=False, help='returns some system information after a p2y')



    def prepare_for_submission(self, tempfolder):

        _dbs_accepted = {'gw0': 'ndb.QP', 'HF_and_locXC': 'ndb.HF_and_locXC',}

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []

        # Settings can be undefined, and defaults to an empty dictionary.
        # They will be used for any input that doen't fit elsewhere.

        settings = self.inputs.settings.get_dict()

        initialise = settings.pop('INITIALISE', None)
        if initialise is not None:
            if not isinstance(initialise, bool):
                raise InputValidationError("INITIALISE must be " " a boolean")

        copy_save = settings.pop('COPY_SAVE', None)
        if copy_save is not None:
            if not isinstance(copy_save, bool):
                raise InputValidationError("COPY_SAVE must be " " a boolean")

        copy_dbs = settings.pop('COPY_DBS', None)
        if copy_dbs is not None:
            if not isinstance(copy_dbs, bool):
                raise InputValidationError("COPY_DBS must be " " a boolean")
        
        restart_yambo = settings.pop('RESTART_YAMBO', None)
        if restart_yambo is not None:
            if not isinstance(restart_yambo, bool):
                raise InputValidationError("RESTART_YAMBO must be " " a boolean")

        parameters = self.inputs.parameters

        if not initialise:
            if not isinstance(parameters, Dict):
                raise InputValidationError("parameters is not of type Dict")

        parent_calc_folder = self.inputs.parent_folder

        main_code = self.inputs.code

        preproc_code = self.inputs.preprocessing_code

        parent_calc = take_calc_from_remote(parent_calc_folder)

        if parent_calc.process_type=='aiida.calculations:yambo.yambo':
            yambo_parent=True
        else:
            yambo_parent=False

        # flags for yambo interfaces
        try:
            precode_param_dict = self.inputs.precode_parameters
        except:
            precode_param_dict = Dict(dict={})
        # check the precode parameters given in input
        input_cmdline = settings.pop('CMDLINE', None)
        import re
        precode_params_list = [] #['cd aiida.save'] ##.format(parent_calc_folder._PREFIX)
        pattern = re.compile(r"(^\-)([a-zA-Z])")
        for key, value in six.iteritems(precode_param_dict.get_dict()):
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

            input_filename = tempfolder.get_abs_path(self.metadata.options.input_filename)

            with open(input_filename, 'w') as infile:
                infile.write(self.metadata.options.logostring)

                for k, v in six.iteritems(boolean_dict):
                    if v:
                        infile.write("{}\n".format(k))

                for this_dict in parameters_list:
                    key = this_dict['key']
                    value = this_dict['value']
                    units = this_dict['units']


                    if isinstance(value, list):
                        value_string = ''
                        try:
                            for v in value:
                                value_string += " | ".join([str(_) for _ in v]) + " |\n"
                        except:
                            value_string += " | ".join([str(_) for _ in value]) + " |\n"

                        the_string = "% {}\n {}".format(key, value_string)
                        the_string += "%"


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

        try:
            parent_calc = parent_calc_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
        except:
            parent_calc = parent_calc_folder.get_incoming().get_node_by_label('remote_folder')

        if yambo_parent:
            if copy_save:
                try:
                    remote_copy_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/SAVE/",'./SAVE/'))
                except:
                    remote_copy_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"out/aiida.save/SAVE/",'./SAVE/'))
            else:
                try:
                    remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/SAVE/",'./SAVE/'))
                except:
                    remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"out/aiida.save/SAVE/",'./SAVE/'))

            if copy_dbs:
                    remote_copy_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/aiida.out/",'./aiida.out/'))
            if restart_yambo:
                    remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/aiida.out/",'./aiida.out/'))
        else:
            remote_copy_list.append(
                (parent_calc_folder.computer.uuid,
                 os.path.join(parent_calc_folder.get_remote_path(),
                              PwCalculation._OUTPUT_SUBFOLDER,
                              "aiida.save","*" ),  ##.format(parent_calc_folder._PREFIX)
                                     "."
                                     )
                                    )
        ############################################
        # set Calcinfo
        ############################################

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid

        calcinfo.local_copy_list = []
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append('r*')
        calcinfo.retrieve_list.append('l*')
        calcinfo.retrieve_list.append('o*')
        calcinfo.retrieve_list.append('LOG/l*_CPU_1')
        calcinfo.retrieve_list.append('LOG/l*_CPU_2')
        calcinfo.retrieve_list.append('*stderr*') #standard errors
        extra_retrieved = []

        if initialise:
        #    extra_retrieved.append('SAVE/'+_dbs_accepted['ns.db1'])
            pass
        else:
            for dbs in _dbs_accepted.keys():
                db = boolean_dict.pop(dbs,False)
                if db:
                    extra_retrieved.append('aiida.out/'+_dbs_accepted[dbs])

        additional = settings.pop('ADDITIONAL_RETRIEVE_LIST',[])
        if additional:
            extra_retrieved.append(additional)

        for extra in extra_retrieved:
            calcinfo.retrieve_list.append(extra)

        from aiida.common.datastructures import CodeRunMode, CodeInfo

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
            try:
                parent_settings = _uppercase_dict(
                    parent_calc.inputs.settings.get_dict(),
                    dict_name='parent settings')
                parent_initialise = parent_settings['INITIALISE']
            except KeyError:
                parent_initialise = False
            c1 = None
            if not parent_initialise:
                c2 = None
        else:
            c1.cmdline_params = precode_params_list
            c1.code_uuid = preproc_code.uuid

        # c3 = yambo calculation
        c3 = CodeInfo()
        c3.withmpi = True
        #c3.withmpi = self.get_withmpi()
        c3.cmdline_params = [
            "-F", self.metadata.options.input_filename, \
            '-J', self.metadata.options.output_filename, \
        ]
        c3.code_uuid = main_code.uuid

        if initialise:
            c2 = None
            c3 = None

        #logic of the execution
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

        calcinfo.codes_run_mode = CodeRunMode.SERIAL

        if settings:
            raise InputValidationError(
                "The following keys have been found in "
                "the settings input node, but were not understood: {}".format(
                    ",".join(list(settings.keys()))))

        return calcinfo

################################################################################
    #the following functions are not used
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
