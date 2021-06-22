# -*- coding: utf-8 -*-
"""helpers for k_path_"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import os

try:
    from aiida.orm import Dict, Str, List, load_node, KpointsData, RemoteData, Group
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida.engine import calcfunction 
except:
    pass

class k_path_dealer():
    
    def __init__(self):
        pass
    
    def get_mesh(self,mesh, kcell):
        t=0
        h=[1,1,1]
        for l in range(len(mesh)):
            if mesh[l] == 1: h[l] = 0
        grid = np.zeros(((mesh[0]+h[0])*(h[1]+mesh[1])*(mesh[2]+h[2]),3))
        for i in range(0,int(mesh[0])+h[0]):
            for j in range(0,int(mesh[1])+h[1]):
                for k in range(0,int(mesh[2])+h[2]):
                    grid[t,:] = np.array([kcell[0]*i/(mesh[0])/2,
                                          kcell[1]*j/(mesh[1])/2,
                                          kcell[2]*k/(mesh[2])/2])
                    t += 1
        return grid
    
    def k_path_G_to_G(self,structure, nkpoints):
        cell = structure.get_cell()
        k_path = cell.bandpath(npoints=nkpoints)
        p = k_path.path.split(',')[0].split('G')
        p_ok = ['G']+[k for k in p[:][1]]+['G']
        mapping = k_path.get_linear_kpoint_axis()
        ticks = []
        names = []
        for i in range(len(mapping[2])):
            ticks.append(np.where(mapping[0] == mapping[1][i])[0][0])
            names.append(mapping[2][i])
        ind = np.where(mapping[0]==mapping[1][mapping[2][1:].index('G')+1])[0][0]
        #needed_kpoints = k_path.kpts[:ind]
        return mapping, ind, {'names':names,'ticks':ticks}
    
    def check_kpoints_in_bare_mesh(self,mesh,kcell,structure,k_list={}):
        grid = self.get_mesh(mesh, kcell)
        cell = structure.get_cell()
        k = cell.bandpath()
        high_symmetry = k.special_points
        missing = [] 
        maps = {}
        for point in high_symmetry.keys():
            ind = 1 
            found = False
            for g in grid:
                if np.allclose(abs(high_symmetry[point]),abs(g),1e-4,1e-4):    #1e-4,1e-4):
                    found = True
                    maps[point] = ind
                    break
                ind += 1
            if not found:
                if point not in missing: missing.append(point)
        
        return missing, maps

    @classmethod
    def check_kpoints_in_qe_grid(self,qe_grid,structure,k_list={}):
        cell = structure.get_cell()
        k = cell.bandpath()
        high_symmetry = k.special_points
        high_symmetry.update(k_list)
        missing = []
        maps = {}
        for point in high_symmetry.keys():
            ind = 1 
            found = False
            for g in qe_grid:
                if np.allclose(abs(high_symmetry[point]),abs(g),1e-4,1e-4):    #1e-4,1e-4):
                    found = True
                    maps[point] = ind
                    break
                elif abs(high_symmetry[point][0])-abs(g[1])<1e-4 and abs(high_symmetry[point][1])-abs(g[0])<1e-4 \
                        and abs(high_symmetry[point][2])-abs(g[2])<1e-4 :    #1e-4,1e-4):
                    found = True
                    maps[point] = ind
                    break
                ind += 1
            if not found:
                if point not in missing: missing.append(point)
                    
        return missing, maps