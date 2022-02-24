from __future__ import absolute_import

import numpy as np
from scipy import optimize
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
from ase import Atoms
from aiida_yambo.utils.common_helpers import *


def generate_convergence_setup():
    pass