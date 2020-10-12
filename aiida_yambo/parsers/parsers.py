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
from aiida.orm import Dict
from aiida.orm import StructureData
from aiida.plugins import DataFactory, CalculationFactory
import glob, os, re

try:
    from yamboparser import *
except: 
    from aiida_yambo.parsers.ext_dep.yambofile import *
    from aiida_yambo.parsers.ext_dep.yambofolder import *

from aiida_yambo.calculations.yambo import YamboCalculation
from aiida_yambo.utils.common_helpers import *
from aiida_yambo.parsers.utils import *

from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.calculations import _lowercase_dict, _uppercase_dict
from six.moves import range
import cmath
import netCDF4


__copyright__ = u"Copyright (c), 2014-2015, École Polytechnique Fédérale de Lausanne (EPFL), Switzerland, Laboratory of Theory and Simulation of Materials (THEOS). All rights reserved."
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file"
__version__ = "0.4.1"
__authors__ = "Michael Atambo, Antimo Marrazzo, Gianluca Prandini and the AiiDA team. The parser relies on the yamboparser module by Henrique Pereira Coutada Miranda."


class YamboParser(Parser):
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
        if calculation.process_type=='aiida.calculations:yambo.yambo':
            yambo_parent=True
        else:
            raise OutputParsingError(
                "Input calculation must be a YamboCalculation, not {}".format(calculation.process_type))

        self._calc = calculation
        self.last_job_info = self._calc.get_last_job_info()
        self._eels_array_linkname = 'array_eels'
        self._eps_array_linkname = 'array_eps'
        self._alpha_array_linkname = 'array_alpha'
        self._qp_array_linkname = 'array_qp'
        self._ndb_linkname = 'array_ndb'
        self._ndb_QP_linkname = 'array_ndb_QP'
        self._ndb_HF_linkname = 'array_ndb_HFlocXC'
        self._lifetime_bands_linkname = 'bands_lifetime'
        self._quasiparticle_bands_linkname = 'bands_quasiparticle'
        self._parameter_linkname = 'output_parameters'
        self._system_info_linkname = 'system_info'
        super(YamboParser, self).__init__(calculation)

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

        # select the folder object
        try:
            out_folder = self.retrieved
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

        parent_calc = find_pw_parent(self._calc)
        cell = parent_calc.inputs.structure.cell

        output_params = {'warnings': [], 'errors': [], 'yambo_wrote_dbs': False, 'game_over': False,
        'p2y_completed': False, 'last_time':0,\
        'requested_time':self._calc.attributes['max_wallclock_seconds'], 'time_units':'seconds',\
        'memstats':[], 'para_error':False, 'memory_error':False,'timing':[],'time_error': False, 'has_gpu': False,
        'yambo_version':'4.5', 'Fermi(eV)':0}
        ndbqp = {}
        ndbhf = {}

        try:
            results = YamboFolder(out_folder._repository._repo_folder.abspath)
        except Exception as e:
            success = False
            return self.exit_codes.PARSER_ANOMALY
            #raise ParsingError("Unexpected behavior of YamboFolder: %s" % e)

        for file in os.listdir(out_folder._repository._repo_folder.abspath):
            if 'stderr' in file:
                with open(file,'r') as stderrZZ:
                    parse_scheduler_stderr(stderr, output_params)

        for result in results.yambofiles:
            if results is None:
                continue

            #This should be automatic in yambopy...
            if result.type=='log':
                parse_log(result, output_params)
            if result.type=='report':
                parse_report(result, output_params)

            if 'eel' in result.filename:
                eels_array = self._aiida_array(result.data)
                self.out(self._eels_array_linkname, eels_array)
            elif 'eps' in result.filename:
                eps_array = self._aiida_array(result.data)
                self.out(self._eps_array_linkname, eps_array)
            elif 'alpha' in result.filename:
                alpha_array = self._aiida_array(result.data)
                self.out(self._alpha_array_linkname,alpha_array)

            elif 'ndb.QP' == result.filename:
                ndbqp = copy.deepcopy(result.data)

            elif 'ndb.HF_and_locXC' == result.filename:
                ndbhf = copy.deepcopy(result.data)

            elif 'gw0___' in input_params:
                if self._aiida_bands_data(result.data, cell, result.kpoints):
                    arr = self._aiida_bands_data(result.data, cell,
                                                 result.kpoints)
                    if type(arr) == BandsData:  # ArrayData is not BandsData, but BandsData is ArrayData
                        self.out(self._quasiparticle_bands_linkname,arr)
                    if type(arr) == ArrayData:  #
                        self.out(self._qp_array_linkname,arr)

            elif 'life___' in input_params:
                if self._aiida_bands_data(result.data, cell, result.kpoints):
                    arr = self._aiida_bands_data(result.data, cell,
                                                 result.kpoints)
                    if type(arr) == BandsData:
                        self.out(self._alpha_array_linkname+'_bands',arr)
                    elif type(arr) == ArrayData:
                        self.out(self._alpha_array_linkname + '_arr', arr)
        
        yambo_wrote_dbs(output_params)

        params=Dict(dict=output_params)
        self.out(self._parameter_linkname,params)  # output_parameters



        # we store  all the information from the ndb.* files rather than in separate files
        # if possible, else we default to separate files.
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
            

        if success == False:
            if abs((float(output_params['last_time'])-float(output_params['requested_time'])) \
                  / float(output_params['requested_time'])) < 0.25: 
                return self.exit_codes.WALLTIME_ERROR
            elif 'time_most_prob' in output_params['errors']:
                return self.exit_codes.WALLTIME_ERROR
            elif output_params['para_error']:
                return self.exit_codes.PARA_ERROR
            elif output_params['memory_error'] and 'X_par_allocation' in output_params['errors']:
                return self.exit_codes.X_par_MEMORY_ERROR              
            elif output_params['memory_error']:
                return self.exit_codes.MEMORY_ERROR
            elif output_params['time_error']:
                return self.exit_codes.WALLTIME_ERROR
            else:
                return self.exit_codes.NO_SUCCESS

    def _aiida_array(self, data):
        arraydata = ArrayData()
        for ky in data.keys():
            arraydata.set_array(ky, data[ky])
        return arraydata

    def _aiida_bands_data(self, data, cell, kpoints_dict):
        if not data:
            return False
        kpt_idx = sorted(data.keys())  #  list of kpoint indices
        try:
            k_list = [kpoints_dict[i]
                      for i in kpt_idx]  # list of k-point triplet
        except KeyError:
            # kpoint triplets are not present (true  for .qp and so on, can not use BandsData)
            # We use the internal Yambo Format  [ [Eo_1, Eo_2,... ], ...[So_1,So_2,] ]
            #                                  QP_TABLE  [[ib_1,ik_1,isp_1]      ,[ib_n,ik_n,isp_n]]
            # Each entry in DATA has corresponding legend in QP_TABLE that defines its details
            # like   ib= Band index,  ik= kpoint index,  isp= spin polarization index.
            #  Eo_1 =>  at ib_1, ik_1 isp_1.
            pdata = ArrayData()
            QP_TABLE = []
            ORD = []
            Eo = []
            E_minus_Eo = []
            So = []
            Z = []
            for ky in data.keys():  # kp == kpoint index as a string  1,2,..
                for ind in range(len(data[ky]['Band'])):
                    try:
                        Eo.append(data[ky]['Eo'][ind])
                    except KeyError:
                        pass
                    try:
                        E_minus_Eo.append(data[ky]['E-Eo'][ind])
                    except KeyError:
                        pass
                    try:
                        So.append(data[ky]['Sc|Eo'][ind])
                    except KeyError:
                        pass
                    try:
                        Z.append(data[ky]['Z'][ind])
                    except KeyError:
                        pass
                    ik = int(ky)
                    ib = data[ky]['Band'][ind]
                    isp = 0
                    if 'Spin_Pol' in list(data[ky].keys()):
                        isp = data[ky]['Spin_Pol'][ind]
                    QP_TABLE.append([ik, ib, isp])
            pdata.set_array('Eo', numpy.array(Eo))
            pdata.set_array('E_minus_Eo', numpy.array(E_minus_Eo))
            pdata.set_array('So', numpy.array(So))
            pdata.set_array('Z', numpy.array(Z))
            pdata.set_array('qp_table', numpy.array(QP_TABLE))
            return pdata
        quasiparticle_bands = BandsData()
        quasiparticle_bands.set_cell(cell)
        quasiparticle_bands.set_kpoints(k_list, cartesian=True)
        # labels will come from any of the keys in the nested  kp_point data,
        # there is a uniform set of observables for each k-point, ie Band, Eo, ...
        # ***FIXME BUG does not seem to handle spin polarizes at all when constructing bandsdata***
        bands_labels = [
            legend for legend in sorted(data[list(data.keys())[0]].keys())
        ]
        append_list = [[] for i in bands_labels]
        for kp in kpt_idx:
            for i in range(len(bands_labels)):
                append_list[i].append(data[kp][bands_labels[i]])
        generalised_bands = [numpy.array(it) for it in append_list]
        quasiparticle_bands.set_bands(
            bands=generalised_bands, units='eV', labels=bands_labels)
        return quasiparticle_bands

    def _aiida_ndb_qp(self, data):
        """
        Save the data from ndb.QP to the db
        """
        pdata = ArrayData()
        pdata.set_array('Eo', numpy.array(data['Eo']))
        pdata.set_array('E_minus_Eo', numpy.array(data['E-Eo']))
        pdata.set_array('Z', numpy.array(data['Z']))
        pdata.set_array('qp_table', numpy.array(data['qp_table']))
        try:
            pdata.set_array('So', numpy.array(data['So']))
        except KeyError:
            pass
        return pdata

    def _aiida_ndb_hf(self, data):
        """Save the data from ndb.HF_and_locXC

        """
        pdata = ArrayData()
        pdata.set_array('Sx', numpy.array(data['Sx']))
        pdata.set_array('Vxc', numpy.array(data['Vxc']))
        return pdata

    def _sigma_c(self, ndbqp, ndbhf):
        """Calculate S_c if missing from  information parsed from the  ndb.*

         Sc = 1/Z[ E-Eo] -S_x + Vxc
        """
        Eo = numpy.array(ndbqp['Eo'])
        Z = numpy.array(ndbqp['Z'])
        E_minus_Eo = numpy.array(ndbqp['E-Eo'])
        Sx = numpy.array(ndbhf['Sx'])
        Vxc = numpy.array(ndbhf['Vxc'])
        try:
            Sc = numpy.array(ndbqp['So'])
        except KeyError:
            Sc = 1 / Z * E_minus_Eo - Sx + Vxc
        pdata = ArrayData()
        pdata.set_array('Eo', Eo)
        pdata.set_array('E_minus_Eo', E_minus_Eo)
        pdata.set_array('Z', Z)
        pdata.set_array('Sx', Sx)
        pdata.set_array('Sc', Sc)
        pdata.set_array('Vxc', Vxc)
        pdata.set_array('qp_table', numpy.array(ndbqp['qp_table']))
        return pdata
