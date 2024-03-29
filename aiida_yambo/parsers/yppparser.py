# -*- coding: utf-8 -*-

from __future__ import absolute_import
from aiida.orm import FolderData
from aiida.parsers.parser import Parser
from aiida.common.exceptions import OutputParsingError
from aiida.common.exceptions import UniquenessError
from aiida.common.exceptions import ValidationError, ParsingError
import numpy
import copy
from aiida.orm import ArrayData
from aiida.orm import BandsData
from aiida.orm import KpointsData
from aiida.orm import Dict, Str
from aiida.orm import StructureData
from aiida.plugins import DataFactory, CalculationFactory
import glob, os, re

from yamboparser.yambofile import *
from yamboparser.yambofolder import *

from aiida_yambo.calculations.yambo import YamboCalculation
from aiida_yambo.utils.common_helpers import *
from aiida_yambo.parsers.utils import *

from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.calculations import _lowercase_dict, _uppercase_dict
from six.moves import range
import cmath
import netCDF4

import pathlib
import tempfile

__copyright__ = u"Copyright (c), 2014-2015, École Polytechnique Fédérale de Lausanne (EPFL), Switzerland, Laboratory of Theory and Simulation of Materials (THEOS). All rights reserved."
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file"
__version__ = "0.4.1"
__authors__ = " Miki Bonacci (miki.bonacci@unimore.it)," \
              " Gianluca Prandini (gianluca.prandini@epfl.ch)," \
              " Antimo Marrazzo (antimo.marrazzo@epfl.ch)," \
              " Michael Atambo (michaelontita.atambo@unimore.it)", \
              " and the AiiDA team. The parser relies on the yamboparser module by Henrique Pereira Coutada Miranda."

SingleFileData = DataFactory('core.singlefile')

class YppParser(Parser):
    """This class is a wrapper class for the Parser class for Yambo calculators from yambopy.

    *IMPORTANT:* This plugin can parse netcdf files produced by yambo if the
    python netcdf libraries are installed, otherwise they are ignored.
    Accepts data from yambopy's YamboFolder  as a list of YamboFile instances.
    The instances of YamboFile have the following attributes:

    ::
      .data: A Dict, with k-points as keys and  in each futher a dict with obeservalbe:value pairs ie. { '1' : {'Eo': 5, 'B':1,..}, '15':{'Eo':5.55,'B': 30}... }
      .warnings:     list of strings, one warning  per string.
      .errors:       list of errors, one error per string.
      .memory        list of string, info on memory allocated and freed
      .max_memory    maximum memory allocated or freed during the run
      .last_memory   last memory allocated or freed during the run
      .last_memory_time   last point in time at which  memory was  allocated or freed
      .*_units       units (e.g. Gb or seconds)
      .wall_time     duration of the run (as parsed from the log file)
      .last_time     last time reported (as parsed from the log file)
      .kpoints: When non empty is a Dict of kpoint_index: kpoint_triplet values i.e.                  { '1':[0,0,0], '5':[0.5,0.0,5] .. }
      .type:   type of file accordParseing to YamboFile types include:
      1. 'report'    : 'r-..' report files
      2. 'output_gw'  : 'o-...qp': quasiparticle output file   ...           .. etc
      N. 'unknown' : when YamboFile was unable to deduce what type of file
      .timing: list of timing info.

    Saved data:

    o-..qp : ArrayData is stored in a format similar to the internal yambo db format (two arrays):
             [[E_o,E-E_o,S_c],[...]]  and
             [[ik,ib,isp],...]
             First is the observables, and the second array contains the kpoint index, band index
             and spin index if spin polarized else 0. BandsData can not be used as the k-point triplets
             are not available in the o-.qp file.

    r-..    : BandsData is stored with the proper list of K-points, bands_labels.

    """

    def __init__(self, calculation):
        """Initialize the instance of YamboParser"""
        from aiida.common import AIIDA_LOGGER
        self._logger = AIIDA_LOGGER.getChild('parser').getChild(
            self.__class__.__name__)
       # check for valid input
        if calculation.process_type=='aiida.calculations:yambo.ypp':
            yambo_parent=True
        else:
            raise OutputParsingError(
                "Input calculation must be a YppCalculation, not {}".format(calculation.process_type))

        self._calc = calculation
        self.last_job_info = self._calc.get_last_job_info()
        self._unsorted_eig_wannier = 'unsorted_eig_file'
        self._qp_array_linkname = 'array_qp'
        self._quasiparticle_bands_linkname = 'bands_quasiparticle'
        self._parameter_linkname = 'output_parameters'
        self._system_info_linkname = 'system_info'
        self._QP_merged_linkname = 'QP_DB'
        super(YppParser, self).__init__(calculation)

    def parse(self, retrieved, **kwargs):
        """Parses the datafolder, stores results.

        This parser for this code ...
        """
        from aiida.common.exceptions import InvalidOperation
        from aiida.common import exceptions
        from aiida.common import AIIDA_LOGGER

        # suppose at the start that the job is unsuccess, unless proven otherwise
        success = False

        # check whether the yambo calc was an initialisation (p2y)
        try:
            settings_dict = self._calc.inputs.settings.get_dict()
            settings_dict = _uppercase_dict(
                settings_dict, dict_name='settings')
        except AttributeError:
            settings_dict = {}

        initialise = settings_dict.pop('INITIALISE', None)
        verbose_timing = settings_dict.pop('T_VERBOSE', False)
            
        # select the folder object
        try:
            retrieved = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        try:
            input_params = self._calc.inputs.parameters.get_dict()
        except AttributeError:
            if not initialise:
                raise ParsingError("Input parameters not found!")
            else:
                input_params = {}
        # retrieve the cell: if parent_calc is a YamboCalculation we must find the original PwCalculation
        # going back through the graph tree.

        output_params = {'warnings': [], 'errors': [], 'yambo_wrote_dbs': False, 'game_over': False,
        'p2y_completed': False, 'last_time':0,\
        'requested_time':self._calc.attributes['max_wallclock_seconds'], 'time_units':'seconds',\
        'memstats':[], 'para_error':False, 'memory_error':False,'timing':[],'time_error': False, 'has_gpu': False,
        'yambo_version':'5.x', 'Fermi(eV)':0,}
        ndbqp = {}
        ndbhf = {}

        # Create temporary directory
        with tempfile.TemporaryDirectory() as dirpath:
            # Open the output file from the AiiDA storage and copy content to the temporary file
            for filename in retrieved.base.repository.list_object_names():
                # Create the file with the desired name
                temp_file = pathlib.Path(dirpath) / filename
                with retrieved.open(filename, 'rb') as handle:
                    temp_file.write_bytes(handle.read())

            count_merged = 0
            for filename in os.listdir(dirpath):
                if 'ndb.QP_merged' in filename:
                    count_merged +=1
            for filename in os.listdir(dirpath):
                if 'stderr' in filename:
                    with open(dirpath+"/"+filename,'r') as stderr:
                        parse_scheduler_stderr(stderr, output_params)
                if 'unsorted' in filename:
                    unsorted_eig = SingleFileData(dirpath+"/"+filename)
                    self.out(self._unsorted_eig_wannier,unsorted_eig)
                    #self.report('stored the unsorted.eig file as SingleFileData')
                if 'ndb.QP_merged' in filename:
                    if count_merged>1:
                        return self.exit_codes.MERGE_NOT_COMPLETE
                    else:
                        QP_db = SingleFileData(dirpath+"/"+filename)
                        self.out(self._QP_merged_linkname,QP_db)  

            try:
                results = YamboFolder(dirpath)
            except Exception as e:
                success = False
                return self.exit_codes.PARSER_ANOMALY
                #raise ParsingError("Unexpected behavior of YamboFolder: %s" % e)
    
            for result in results.yambofiles:
                if results is None:
                    continue
    
                #This should be automatic in yambopy...
                if result.type=='log':
                    parse_log(result, output_params, timing = verbose_timing)
                if result.type=='report':
                    parse_report(result, output_params)
    
                if 'electrons' in input_params['arguments'] and 'interpolated' in result.filename:
                    if self._aiida_bands_data(result.data, cell, result.kpoints):
                        arr = self._aiida_bands_data(result.data, cell,
                                                     result.kpoints)
                        if type(arr) == BandsData:  # ArrayData is not BandsData, but BandsData is ArrayData
                            self.out(self._quasiparticle_bands_linkname,arr)
                        if type(arr) == ArrayData:  #
                            self.out(self._qp_array_linkname,arr)
        
            yambo_wrote_dbs(output_params)

            # we store  all the information from the ndb.* files rather than in separate files
            # if possible, else we default to separate files. #to check MB
            if ndbqp and ndbhf:  #
                self.out(self._ndb_linkname,self._sigma_c(ndbqp, ndbhf))
            else:
                if ndbqp:
                    self.out(self._ndb_QP_linkname,self._aiida_ndb_qp(ndbqp))
                if ndbhf:
                    self.out(self._ndb_HF_linkname,self._aiida_ndb_hf(ndbhf))

        if output_params['game_over']:
            success = True
        elif output_params['p2y_completed'] and initialise:
            success = True
        
        #last check on time
        delta_time = (float(output_params['requested_time'])-float(output_params['last_time'])) \
                  / float(output_params['requested_time'])
        
        if success == False:
            if delta_time > -2 and delta_time < 0.1:
                    output_params['time_error']=True

        params=Dict(output_params)
        self.out(self._parameter_linkname,params)  # output_parameters

        if success == False:
            return self.exit_codes.NO_SUCCESS
