# -*- coding: utf-8 -*-
"""
Plugin to create a YPP input file and run a calculation with the ypp executable.
"""
from __future__ import absolute_import
import os
from tokenize import Single
import six

from aiida.engine import CalcJob

from aiida_quantumespresso.calculations import _lowercase_dict, _uppercase_dict

from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import CalcJobState
from aiida.common.exceptions import UniquenessError, InputValidationError, ValidationError
from aiida.common.utils import classproperty

from aiida.orm import Code
from aiida.orm.nodes import Dict
from aiida.orm.nodes import RemoteData, BandsData, ArrayData, FolderData

from aiida.plugins import DataFactory, CalculationFactory

from aiida.common import AIIDA_LOGGER
from aiida.common import LinkType

from aiida_yambo.utils.common_helpers import * 

from yambopy.io.inputfile import YamboIn

PwCalculation = CalculationFactory('quantumespresso.pw')
YamboCalculation = CalculationFactory('yambo.yambo')
SingleFileData = DataFactory('singlefile')

__authors__ = " Miki Bonacci (miki.bonacci@unimore.it)," \
              " Nicola Spallanzani" \


class YppCalculation(CalcJob):
    """
    AiiDA plugin for the Ypp code.
    For more information, refer to http://www.yambo-code.org/
    https://github.com/yambo-code/yambo-aiida and http://aiida-yambo.readthedocs.io/en/latest/
    """

    # Default input and output files
    _DEFAULT_INPUT_FILE = 'ypp.in'
    _DEFAULT_OUTPUT_FILE = 'aiida.out'

    @classmethod
    def define(cls,spec):
        super(YppCalculation, cls).define(spec)
        spec.input('metadata.options.input_filename', valid_type=six.string_types, default=cls._DEFAULT_INPUT_FILE)
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._DEFAULT_OUTPUT_FILE)

       # Default output parser provided by AiiDA
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default='yambo.ypp')

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
#             AIIDA input plugin.  YAMBO >4.0 compatible
#               http://www.yambo-code.org
#
"""
)


        spec.input('settings',valid_type=Dict,
                default=Dict(dict={'COPY_DBS':True}),
                help='Use an additional node for special settings')
        spec.input('parameters',valid_type=Dict,
                help='Use a node that specifies the input parameters')
        spec.input('parent_folder',valid_type=RemoteData,required=False,
                help='Use a remote folder as parent folder (for "restarts and similar"')
        
        spec.input('code',valid_type=Code,
                help='Use a main code for ypp calculation')
        
        spec.input(
            'nnkp_file',
            valid_type=SingleFileData,
            required=False,
            help=
            'The nnkp file'
        )

        spec.input(
            'QP_DB',
            valid_type=SingleFileData,
            required=False,
            help=
            'The QP_DB file'
        )

        spec.input(
            'QP_calculations',
            valid_type=List,
            required=False,
            help='List of QP pk/uuid calculations that you want to merge.')

        spec.input(
            'QP_DB_List',
            valid_type=List,
            required=False,
            help='List of QP pk/uuid SingleFileData that you want to merge.')

        spec.exit_code(500, 'ERROR_NO_RETRIEVED_FOLDER',
                message='The retrieved folder data node could not be accessed.')
        spec.exit_code(501, 'WALLTIME_ERROR',
                message='time exceeded the max walltime')
        spec.exit_code(502, 'NO_SUCCESS',
                message='failed calculation for unknown reason')
        spec.exit_code(503, 'PARSER_ANOMALY',
                message='Unexpected behavior of YamboFolder')
        spec.exit_code(504, 'NNKP_NOT_PRESENT',
                message='nnkp file not present')
        spec.exit_code(505, 'QP_LIST_NOT_PRESENT',
                message='QP list not present')
        spec.exit_code(506, 'MERGE_NOT_COMPLETE',
                message='QP merging is not completed.')
        spec.exit_code(507, 'PARENT_NOT_VALID',
                message='parent folder not valid. It has not a QP_DB node as output..')
        #outputs definition:

        spec.output('output_parameters', valid_type=Dict,
                required=True, help='returns the output parameters')
        spec.output('array_interpolated_bands', valid_type=ArrayData,
                required=False, help='returns the interpolated bands array')
        spec.output(
            'unsorted_eig_file',
            valid_type=SingleFileData,
            required=False,
            help='The ``.unsorted.eig`` file.'
        )
        spec.output('QP_DB', valid_type=SingleFileData,
                required=False, help='returns the singlefiledata for ndbQP')


    def prepare_for_submission(self, tempfolder):

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []

        # Settings can be undefined, and defaults to an empty dictionary.
        # They will be used for any input that doen't fit elsewhere.

        settings = self.inputs.settings.get_dict()

        copy_save = settings.pop('COPY_SAVE', None)
        if copy_save is not None:
            if not isinstance(copy_save, bool):
                raise InputValidationError("COPY_SAVE must be " " a boolean")

        copy_dbs = settings.pop('COPY_DBS', None)
        if copy_dbs is not None:
            if not isinstance(copy_dbs, bool):
                raise InputValidationError("COPY_DBS must be " " a boolean")
        
        link_dbs = settings.pop('LINK_DBS', None)
        if link_dbs is not None:
            if not isinstance(link_dbs, bool):
                raise InputValidationError("LINK_DBS must be " " a boolean")
        
        verbose_timing = settings.pop('T_VERBOSE', None)
        if verbose_timing is not None:
            if not isinstance(verbose_timing, bool):
                raise InputValidationError("T_VERBOSE must be " " a boolean")
            
        parameters = self.inputs.parameters

        if not isinstance(parameters, Dict):
            raise InputValidationError("parameters is not of type Dict")

        parent_calc_folder = self.inputs.parent_folder

        main_code = self.inputs.code

        try:
            parent_calc = take_calc_from_remote(parent_calc_folder,level=-1)
        except:
            parent_calc = take_calc_from_remote(parent_calc_folder,level=0)

        yambo_parent = False
        ypp_parent=True

        if parent_calc.process_type=='aiida.calculations:yambo.yambo':
            yambo_parent=True
        elif parent_calc.process_type=='aiida.workflows:yambo.yambo.yamborestart':
            yambo_parent=True
        elif parent_calc.process_type=='aiida.workflows:yambo.yambo.yambowf':
            yambo_parent=True
        elif parent_calc.process_type=='aiida.workflows:yambo.yambo.yamboconvergence':
            yambo_parent=True
        elif parent_calc.process_type=='aiida.calculations:yambo.ypp':
            ypp_parent=True
        elif parent_calc.process_type=='aiida.workflows:yambo.ypp.ypprestart':
            ypp_parent=True
        else:
            raise InputValidationError("YppCalculation parent MUST be a YamboCalculation, not {}".format(parent_calc.process_type))

        # TODO: check that remote data must be on the same computer

        ##############################
        # END OF INITIAL INPUT CHECK #
        ##############################


        ###################################################
        # Prepare ypp input file
        ###################################################

        params_dict = parameters.get_dict()

        if 'wannier' in params_dict['arguments']:
            #copy_dbs = True
            copy_save = True
            if not hasattr(self.inputs,'nnkp_file'): 
                self.report('WARNING: aiida.nnkp file not present in inputs, Needed.')
                return self.exit_codes.NNKP_NOT_PRESENT
            else:
                local_copy_list.append((self.inputs.nnkp_file.uuid, self.inputs.nnkp_file.filename, 'aiida.nnkp'))
            
            if hasattr(self.inputs,'QP_DB'): 
                local_copy_list.append((self.inputs.QP_DB.uuid, self.inputs.QP_DB.filename, 'ndb.QP')) #in this way also "ndb.QP_merged_ppa" should be copied ok.
            if not hasattr(self.inputs,'QP_DB') and hasattr(self.inputs,'parent_folder'): 
                try:
                    local_copy_list.append((take_calc_from_remote(self.inputs.parent_folder).outputs.QP_DB.uuid, self.inputs.QP_DB.filename, 'ndb.QP'))
                except:
                    return self.exit_codes.PARENT_NOT_VALID
            
            params_dict['variables']['Seed'] = 'aiida' #self.metadata.options.input_filename.replace('.in','') # depends on the QE seedname, I guess

        if 'QPDB_merge' in params_dict['arguments']:
            copy_save = True
            
            if not hasattr(self.inputs,'QP_calculations') and not ypp_parent: 
                self.report('WARNING: QP_calculations list or folders not present in inputs, Needed.')
                return self.exit_codes.QP_LIST_NOT_PRESENT
            
            j=0
            list_of_dbs = []
            if hasattr(self.inputs,'QP_calculations'):
                for calc in self.inputs.QP_calculations.get_list():
                    j+=1
                    qp = load_node(calc).outputs.QP_db
                    local_copy_list.append((qp.uuid, qp.filename, 'ndb.QP_'+str(j)))
                    list_of_dbs.append(['"E"','"+"','"1"','"'+'ndb.QP_'+str(j)+'"'])
            
            elif hasattr(self.inputs,'QP_DB_List'):
                for calc in self.inputs.QP_DB_List.get_list():
                    j+=1
                    qp = load_node(calc)
                    local_copy_list.append((qp.uuid, qp.filename, 'ndb.QP_'+str(j)))
                    list_of_dbs.append(['"E"','"+"','"1"','"'+'ndb.QP_'+str(j)+'"'])

            elif not hasattr(self.inputs,'QP_calculations') and ypp_parent:
                ypp_parent_calc = take_calc_from_remote(self.inputs.parent_folder)
                for file in os.listdir(ypp_parent_calc.outputs.retrieved._repository._repo_folder.abspath+'/path/'):
                    if 'ndb.QP' in file:
                    #qp = load_node(calc).outputs.QP_db
                        #local_copy_list.append((qp.uuid, qp.filename, 'ndb.QP_'+str(j)))
                        list_of_dbs.append(['"E"','"+"','"1"','"'+file+'"'])
            
            
            params_dict['variables']['Actions_and_names'] = [list_of_dbs,'']
            
        y = YamboIn().from_dictionary(params_dict)

        input_filename = tempfolder.get_abs_path(self.metadata.options.input_filename)

        y.write(input_filename, prefix=self.metadata.options.logostring)
        

        ############################################
        # set copy of the parent calculation
        ############################################

        try:
            parent_calc = parent_calc_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
        except:
            parent_calc = parent_calc_folder.get_incoming().get_node_by_label('remote_folder')

        if copy_save:
                remote_copy_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/SAVE/",'./SAVE/'))
        else:
            try:
                remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/SAVE/",'./SAVE/'))
            except:
                remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"out/aiida.save/SAVE/",'./SAVE/'))

        if copy_dbs:
                remote_copy_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/aiida.out/",'./aiida.out/'))
        if link_dbs:
                remote_symlink_list.append((parent_calc_folder.computer.uuid,parent_calc_folder.get_remote_path()+"/aiida.out/",'./aiida.out/'))
        
        ############################################
        # set Calcinfo
        ############################################

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid

        calcinfo.local_copy_list = local_copy_list   #here I need to append the nnkp_file...
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append('r*')
        calcinfo.retrieve_list.append('l*')
        calcinfo.retrieve_list.append('o*')
        calcinfo.retrieve_list.append('LOG/l*_CPU_1')
        #calcinfo.retrieve_list.append('LOG/l*_CPU_2')
        calcinfo.retrieve_list.append('*stderr*') #standard errors
        extra_retrieved = []

        if 'wannier' in params_dict['arguments']:
            calcinfo.retrieve_list.append('*eig')
            calcinfo.retrieve_list.append('*nnkp')

        if 'QPDB_merge' in params_dict['arguments']:
            calcinfo.retrieve_list.append('SAVE/ndb.QP_merged*')
            calcinfo.retrieve_list.append('aiida.out/ndb.QP_merged*')
        
        additional = settings.pop('ADDITIONAL_RETRIEVE_LIST',[])
        if additional:
            extra_retrieved.append(additional)

        from aiida.common.datastructures import CodeRunMode, CodeInfo

        # c = ypp calculation
        c = CodeInfo()
        c.withmpi = True
        #c.withmpi = self.get_withmpi()

        # Here we need something more flexible, because it is not always like that. 
        # Like something automatic, where you specify 'interpolate bands' or 'excitonic wavefunctions...'
        c.cmdline_params = [
            "-F", self.metadata.options.input_filename, \
            '-J', self.metadata.options.output_filename, \
        ]

        c.code_uuid = main_code.uuid

        #logic of the execution
        calcinfo.codes_info = [c]
        calcinfo.codes_run_mode = CodeRunMode.SERIAL

        for extra in extra_retrieved:
            calcinfo.retrieve_list.append(extra)


        return calcinfo