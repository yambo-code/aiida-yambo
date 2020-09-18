# -*- coding: utf-8 -*-
"""helpers for many purposes"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import os

try:
    from aiida.orm import Dict, Str, List, load_node, KpointsData, RemoteData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida.engine import calcfunction 
except:
    pass

namelists = {'4.5':{'DIP':'_','X':'_','SE':'_'},
             '4.1':{'DIP':'_','X':'_and_IO_','SE':'_'},
            }


def check_para_namelists(params, version):
    
    new_params = {}

    for key in params.keys():
        for level in namelists[version].keys():
            if level in key and '_CPU' in key:
                if level+namelists[version][level]+'CPU' == key:
                    pass
                else:
                    new_params[level+namelists[version][level]+'CPU'] = params[key]

            if level in key and 'ROLEs' in key:
                if level+namelists[version][level]+'ROLEs' == key:
                    pass
                else:
                    new_params[level+namelists[version][level]+'ROLEs'] = params[key]

    if new_params == {}:
        return None
    else:
        return new_params