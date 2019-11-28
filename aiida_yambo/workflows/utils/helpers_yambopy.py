# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
except:
    pass

################################################################################
################################################################################

class calc_manager_yambopy: #the interface class to AiiDA... could be separated fro aiida and yambopy

    def __init__(self, calc_info):

        for key in calc_info.keys():
            setattr(self, str(key), calc_info[key])

        pass

################################## update_parameters #####################################
    def updater(self, inp_to_update, k_distance, first):    #parameter list? yambopy philosophy
        pass

################################## parsers #####################################
    def take_quantities(self, start = 1):

        backtrace = self.steps #*self.iter
        where = self.where
        what = self.what

        pass

#######################################################
    def get_caller(self, calc, depth = 2):

        for i in range(depth):

            pass

        return calc

    def get_called(self, calc, depth = 2):

        for i in range(depth):

            pass

        return calc

    def update_converged_parameters(self, node, params):

        pass
