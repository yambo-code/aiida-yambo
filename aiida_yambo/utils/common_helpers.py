# -*- coding: utf-8 -*-
"""helpers for many purposes"""
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


def find_parent(calc):

    try:
        parent_calc = calc.inputs.parent_folder.get_incoming().all_nodes()[-1] #to load the node from a workchain...
    except:
        parent_calc = calc.inputs.parent_folder.get_incoming().get_node_by_label('remote_folder')
    return parent_calc

def find_pw_parent(parent_calc):

    has_found_pw = False
    while (not has_found_pw):
        if parent_calc.process_type=='aiida.calculations:yambo.yambo':
            has_found_pw = False
                parent_calc = find_parent(parent_calc)
                if parent_calc.process_type=='aiida.calculations:quantumespresso.pw':
                    has_found_pw = True
        elif parent_calc.process_type=='aiida.calculations:quantumespresso.pw':
            has_found_pw = True

    return parent_calc