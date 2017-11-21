# -*- coding: utf-8 -*-
"""
Plugin to create a Yambo input file.
"""
import os
from aiida.orm.calculation.job import JobCalculation
from aiida.common.exceptions import InputValidationError,ValidationError
from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import calc_states
from aiida_quantumespresso.calculations import  get_input_data_text,_lowercase_dict,_uppercase_dict
from aiida.common.exceptions import UniquenessError, InputValidationError
from aiida.common.utils import classproperty
from aiida.orm.data.parameter import ParameterData 
from aiida.orm.data.remote import RemoteData 
from aiida.orm.utils import DataFactory, CalculationFactory
from aiida.orm.code import Code
from aiida.common import aiidalogger
from aiida.common.links import LinkType
PwCalculation = CalculationFactory('quantumespresso.pw')

__copyright__ = u"Copyright (c), 2014-2015, École Polytechnique Fédérale de Lausanne (EPFL), Switzerland, Laboratory of Theory and Simulation of Materials (THEOS). All rights reserved."
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file"
__version__ = "0.4.1"
__authors__ = "Gianluca Prandini, Antimo Marrazzo, Michael Atambo and the AiiDA team."
    
class YamboCalculation(JobCalculation):
    """
    Yambo code.
    For more information, refer to http://www.yambo-code.org/
    """

    def _init_internal_params(self):
        super(YamboCalculation, self)._init_internal_params()

        self._INPUT_FILE_NAME = 'aiida.in'
        
        #Maybe the output name is not necessary...
        self._OUTPUT_FILE_NAME = 'aiida'
    
        # Default output parser provided by AiiDA
        self._default_parser = 'yambo.yambo'
        
        # Default input and output files
        self._DEFAULT_INPUT_FILE = 'aiida.in'
        self._DEFAULT_OUTPUT_FILE = 'aiida.out'

        self._SCRATCH_FOLDER = 'SAVE'

        self._LOGOSTRING = """#                                                           
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

    @classproperty
    def _use_methods(cls):
        """
        Additional use_* methods for the YamboCalculation class.
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "settings": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'settings',
               'docstring': "Use an additional node for special settings",
               },
            "parameters": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'parameters',
               'docstring': ("Use a node that specifies the input parameters "
                             "for the namelists"),
               },
            "parent_folder": {
               'valid_types': RemoteData,
               'additional_parameter': None,
               'linkname': 'parent_calc_folder',
               'docstring': ("Use a remote folder as parent folder (for "
                             "restarts and similar"),
               },
            "preprocessing_code": {'valid_types': Code,
                                   'additional_parameter': None,
                                   'linkname': 'preprocessing_code',
                                   'docstring': ("Use a preprocessing code for "
                                                 "starting yambo"),
               },
            "precode_parameters": {
                                   'valid_types': ParameterData,
                                   'additional_parameter': None,
                                   'linkname': 'precode_parameters',
                                   'docstring': ("Use a node that specifies the input parameters "
                                                 "for the yambo precode"),
               },
            })
        return retdict
    
    def _prepare_for_submission(self, tempfolder, inputdict):        
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.
        
        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (with the Code(s)!)
        """
#        from aiida.common.utils import get_unique_filename, get_suggestion

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        
        # Settings can be undefined, and defaults to an empty dictionary.
        # They will be used for any input that doen't fit elsewhere.
        settings = inputdict.pop(self.get_linkname('settings'),None)
        if settings is None:
            settings_dict = {}
        else:
            if not isinstance(settings,  ParameterData):
                raise InputValidationError("settings, if specified, must be of "
                                           "type ParameterData")
            # Settings converted to uppercase
            settings_dict = _uppercase_dict(settings.get_dict(),
                                            dict_name='settings')
        initialise = settings_dict.pop('INITIALISE', None)
        if initialise is not None:
            if not isinstance(initialise, bool):
                raise InputValidationError("INITIALISE must be "
                                       " a boolean")
        try:
            parameters = inputdict.pop(self.get_linkname('parameters'))
        except KeyError:
            if not initialise:
                raise InputValidationError("No parameters specified for this calculation")
            else:    
                pass
        if not initialise:
            if not isinstance(parameters, ParameterData):
                raise InputValidationError("parameters is not of type ParameterData")

        parent_calc_folder = inputdict.pop(self.get_linkname('parent_folder'),None)
        if parent_calc_folder is None:
            raise InputValidationError("No parent calculation found, it is needed to "
                                       "use Yambo")
        if not isinstance(parent_calc_folder, RemoteData):
            raise InputValidationError("parent_calc_folder must be of"
                                       " type RemoteData")
        
        ### !!!!!! ###
        main_code = inputdict.pop(self.get_linkname('code'),None)
        if main_code is None:
            raise InputValidationError("No input code found!")
        
        
        preproc_code =  inputdict.pop(self.get_linkname('preprocessing_code'),None)
        if preproc_code is not None:
            if not isinstance(preproc_code, Code):
                raise InputValidationError("preprocessing_code, if specified,"
                                           "must be of type Code")
        
        
        parent_calc = parent_calc_folder.get_inputs_dict(link_type=LinkType.CREATE)['remote_folder']
        yambo_parent = isinstance(parent_calc, YamboCalculation)
        
        # flags for yambo interfaces
        try:
            precode_parameters = inputdict.pop(self.get_linkname
                                               ('precode_parameters'))
        except KeyError:
            precode_parameters = ParameterData(dict={})
        if not isinstance(precode_parameters,ParameterData):
            raise InputValidationError('precode_parameters is not '
                                       'of type ParameterData')
        precode_param_dict = precode_parameters.get_dict()

        # check the precode parameters given in input
        input_cmdline = settings_dict.pop('CMDLINE', None)
        import re
        precode_params_list = []
        pattern = re.compile(r"(^\-)([a-zA-Z])")
        for key, value in precode_param_dict.iteritems():
            if re.search(pattern, key) is not None:
                if key == '-O' or key == '-H' or key == '-h' or key == '-F': 
                    raise InputValidationError("Precode flag {} is not allowed".format(str(key)))
                else:   
                    if  precode_param_dict[key] is True:
                        precode_params_list.append(str(key))   
                    elif  precode_param_dict[key] is False:
                        pass            
                    else:
                        precode_params_list.append('{}'.format(str(key)))
                        precode_params_list.append('{}'.format(str(value)))
            else:
                raise InputValidationError("Wrong format of precode_parameters")   
        # Adding manual cmdline input (e.g. for DB fragmentation) 
        if input_cmdline is not None: 
            precode_params_list = precode_params_list + input_cmdline
        
        # TODO: remotedata must be on the same computer 

        ##############################
        # END OF INITIAL INPUT CHECK #
        ##############################

        
        if not initialise:
        ###################################################
        # Prepare yambo input file
        ###################################################
        
            params_dict = parameters.get_dict()
            
            # extract boolean keys
            boolean_dict = { k:v for k,v in params_dict.iteritems() if isinstance(v,bool) }
            params_dict = { k:v for k,v in params_dict.iteritems() if k not in boolean_dict.keys() }
            
            # reorganize the dictionary and create a list of dictionaries with key, value and units
            parameters_list = []
            for k,v in params_dict.iteritems():
                
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
                
                parameters_list.append( this_dict )
            
            input_filename = tempfolder.get_abs_path(self._INPUT_FILE_NAME)
            
            ## create an empty folder for the Yambo scratch
            #tempfolder.get_subfolder(self._SCRATCH_FOLDER, create=True)
            
            with open(input_filename,'w') as infile:
                infile.write( self._LOGOSTRING)
                
                for k,v in boolean_dict.iteritems():
                    if v:
                        infile.write( "{}\n".format(k) )
                
    #         .format(key.lower(), value_string)   
                
                for this_dict in parameters_list:
                    key = this_dict['key']
                    value = this_dict['value']
                    units = this_dict['units']
                
                    if isinstance(value,(tuple,list)):
                        # write the input flags for the Drude term and for the parallelization options of vers. 4 
                        # (it can be implemented in a better way)
                        if key.startswith('DrudeW'):
                            value_string = " ( " + ",".join([str(_) for _ in value]) + " )"
                            the_string = "{} = {}".format(key, value_string)
                            the_string += " {}".format(units)
                            infile.write( the_string + "\n" )
                            continue
                        
                        if key == 'SE_CPU':
                            value_string = " \" " + " ".join([str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write( "SE_ROLEs = \" q qp b  \" " + "\n" )
                            infile.write( the_string + "\n" )
                            continue
                        
                        if key == 'X_all_q_CPU':
                            value_string = " \" " + " ".join([str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write( "X_all_q_ROLEs = \" q k c v  \" " + "\n" )
                            infile.write( the_string + "\n" )
                            continue
                        
                        if key == 'X_finite_q_CPU':
                            value_string = " \" " + " ".join([str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write( "X_finite_q_ROLEs = \" q k c v  \" " + "\n" )
                            infile.write( the_string + "\n" )
                            continue
                        
                        if key == 'X_q_0_CPU':
                            value_string = " \" " + " ".join([str(_) for _ in value]) + " \" "
                            the_string = "{} = {}".format(key, value_string)
                            infile.write( "X_q_0_ROLEs = \" k c v  \" " + "\n" )
                            infile.write( the_string + "\n" )
                            continue
                        
                        if key == 'QPkrange' or key == 'QPerange':
                            value_string = ''
                            for v in value:
                                value_string += " | ".join([str(_) for _ in v]) + " |\n"    
                            the_string = "% {}\n {}".format(key, value_string)    
                            the_string += "%"  
                            infile.write( the_string + "\n" )
                            continue    
                                                             
                        value_string = " | ".join([str(_) for _ in value]) + " |"
                        the_string = "% {}\n {}".format(key, value_string)
                        if units is not None:
                            the_string += " {}".format(units)
                        the_string += "\n%"
                            
                    else:
                        the_value = '"{}"'.format(value) if isinstance(value,basestring) else '{}'.format(value)
                        the_string = "{} = {}".format(key, the_value)
                        if units is not None:
                            the_string += " {}".format(units)
    
                    infile.write( the_string + "\n" )


        ############################################
        # set copy of the parent calculation
        ############################################
        
        parent_calcs = parent_calc_folder.get_inputs(link_type=LinkType.CREATE)
        if len(parent_calcs)>1:
            raise UniquenessError("More than one parent totalenergy calculation" 
                                  "has been found for parent_calc_folder {}".format(parent_calc_folder))
        if len(parent_calcs)==0:
            raise InputValidationError("No parent calculation associated with parent_folder {}".format(parent_calc_folder))
        parent_calc = parent_calcs[0]
        
        if yambo_parent:
            try:
                parent_settings = _uppercase_dict(parent_calc.inp.settings.get_dict(),
                                            dict_name='parent settings')
                parent_initialise = parent_settings['INITIALISE']
            except KeyError:
                parent_initialise = False
        
        if yambo_parent:
            remote_copy_list.append(
                                    (
                                     parent_calc_folder.get_computer().uuid,
                                     os.path.join(parent_calc_folder.get_remote_path(),"SAVE"),
                                     "SAVE/"
                                     )
                                    )
            if not parent_initialise:
                cancopy = False
                if parent_calc.get_state() == calc_states.FINISHED:
                    cancopy = True
                if 'yambo_wrote' in  parent_calc.get_outputs_dict()['output_parameters'].get_dict().keys():
                    if parent_calc.get_outputs_dict()['output_parameters'].get_dict()['yambo_wrote'] == True: 
                        cancopy = True 
                    if parent_calc.get_outputs_dict()['output_parameters'].get_dict()['yambo_wrote'] == False: 
                        cancopy = False 
                if cancopy:
                    remote_copy_list.append(
                                       (
                                         parent_calc_folder.get_computer().uuid,
                                         os.path.join(parent_calc_folder.get_remote_path(),"aiida"),
                                         "aiida/"
                                         )
                                        )
        else:    
            remote_copy_list.append(
                                    (
                                     parent_calc_folder.get_computer().uuid,
                                     os.path.join(parent_calc_folder.get_remote_path(),
                                                  PwCalculation._OUTPUT_SUBFOLDER,
                                                  "{}.save".format(parent_calc._PREFIX),"*" ),
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
        calcinfo.remote_symlink_list = []# remote_symlink_list
        #calcinfo.stdout_name = None # self._OUTPUT_FILE_NAME
        
        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []
        #calcinfo.retrieve_list.append(self._OUTPUT_FILE_NAME)
        calcinfo.retrieve_list.append('r*')
        calcinfo.retrieve_list.append('l*')
        calcinfo.retrieve_list.append('o*')        
        calcinfo.retrieve_list.append('LOG/l-*_CPU_1')        
        extra_retrieved = settings_dict.pop('ADDITIONAL_RETRIEVE_LIST', ['aiida/ndb.QP','aiida/ndb.HF_and_locXC'])
        for extra in extra_retrieved:
            calcinfo.retrieve_list.append( extra )
        
#        # Empty command line by default
#        cmdline_params = settings_dict.pop('CMDLINE', [])
#        calcinfo.cmdline_params = (list(cmdline_params)
#                                   + ["-F", self._INPUT_FILE_NAME, '-J', self._OUTPUT_FILE_NAME])
        
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
        c3.cmdline_params = ["-F", self._INPUT_FILE_NAME, '-J', self._OUTPUT_FILE_NAME]
        c3.code_uuid = main_code.uuid
        
        if initialise:
            c2 = None
            c3 = None
        
        #calcinfo.codes_info = [c1, c2, c3] if not yambo_parent else [c3]
        if yambo_parent:
            if not parent_initialise:
                calcinfo.codes_info=[c3]
            else:
                calcinfo.codes_info=[c2,c3]
        elif initialise:
            calcinfo.codes_info=[c1]
        else:
            calcinfo.codes_info=[c1, c2, c3] 
             
        calcinfo.codes_run_mode = code_run_modes.SERIAL


        if settings_dict:
            raise InputValidationError("The following keys have been found in "
                "the settings input node, but were not understood: {}".format(
                ",".join(settings_dict.keys())))

        return calcinfo
      
        
    def _check_valid_parent(self,calc):
        """
        Check that calc is a valid parent for a YamboCalculation.
        It can be a PwCalculation or a YamboCalculation.
        """

        try:
            if ( (not isinstance(calc,PwCalculation)) 
                  and (not isinstance(calc,YamboCalculation)) ):
                raise ValueError("Parent calculation must be a PwCalculation or a YamboCalculation")
                               
        except ImportError:
            if ( (not isinstance(calc,PwCalculation)) 
                            and (not isinstance(calc,YamboCalculation)) ):
                raise ValueError("Parent calculation must be a PwCalculation or a YamboCalculation")
                            
    
    def use_parent_calculation(self,calc):
        """
        Set the parent calculation of Yambo, 
        from which it will inherit the outputsubfolder.
        The link will be created from parent RemoteData to YamboCalculation 
        """
        from aiida.common.exceptions import NotExistent
        
        self._check_valid_parent(calc)
        
        remotedatas = calc.get_outputs(type=RemoteData)
        if not remotedatas:
            raise NotExistent("No output remotedata found in "
                                  "the parent")
        if len(remotedatas) != 1:
            raise UniquenessError("More than one output remotedata found in "
                                  "the parent")
        remotedata = remotedatas[0]
        
        self._set_parent_remotedata(remotedata)

    def _set_parent_remotedata(self,remotedata):
        """
        Used to set a parent remotefolder in the start of Yambo.
        """
        if not isinstance(remotedata,RemoteData):
            raise ValueError('remotedata must be a RemoteData')
        
        # complain if another remotedata is already found
        input_remote = self.get_inputs(node_type=RemoteData)
        if input_remote:
            raise ValidationError("Cannot set several parent calculation to a "
                                  "Yambo calculation")

        self.use_parent_folder(remotedata)
