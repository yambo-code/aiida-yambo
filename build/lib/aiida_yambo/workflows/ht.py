# -*- coding: utf-8 -*-
"""HT experiment."""
from __future__ import absolute_import
from six.moves import zip

from aiida_yambo.workflows.utils.collectors import * 
from aiida_yambo.workflows.utils.plotting import * 
from aiida_yambo.workflows.utils.fitting import * 
from aiida_yambo.utils.common_helpers import * 
from aiida_yambo.workflows.launch_script import build_builder
from scipy import optimize
import json
from aiida.orm import Group, StructureData,QueryBuilder, KpointsData
from aiida.engine import submit
from aiida.engine import WorkChain, ToContext, calcfunction
from aiida.orm import Code, Dict, Float, Str, StructureData
from aiida.plugins import CalculationFactory

class HighThroughput(WorkChain):
    """WorkChain to compute HT on M100."""

    @classmethod
    def define(cls, spec):
        """Specify inputs and outputs."""
        super(HighThroughput, cls).define(spec)
        spec.input('systems_labels', valid_type=List) #supposing you have already the structures...
        spec.input('parent_query',valid_type=List) #where to query for checking parents
        
        spec.outline(
            cls.setup,
            cls.run_all,
            cls.results,
        )

    def setup(self):
        """Run calculations for equation of state."""
        self.ctx.systems = self.inputs.systems_labels.get_list()
        self.ctx.par_lab = self.inputs.parent_query.get_list()
        self.ctx.par_qb = QueryBuilder()
        self.ctx.par_qb.append(WorkChainNode, filters={'label':{'or':self.ctx.par_lab}})
        
        self.ctx.calculations=[]
        
        for sys in self.ctx.systems:
            self.ctx.calculations.append({sys:{'parent':None,'space':None,'pre':None}})
        
        
        for par in self.ctx.par_qb.all():
            if par[0].label.split()[0] in self.ctx.systems:
                self.report('parent found for {}'.format(par[0].label.split()[0])) 
                #dict_pre = inspect_parent(par[0].pk)
                
        
    def run_all(self):
        """Process."""
        c = {}
        for calc in self.ctx.calculations:
            q = calc[list(calc.keys())[0]]
            if q['space']:
                para_space=q['space']
            else:
                bands_basic = [1000,2000,3000,4000]
                Ry_basic = [3,4,5,6]

                b_n = []
                R_n = []
                space = []
                for b in bands_basic:
                    for r in Ry_basic:
                        space.append([[1,b],[1,b],r])
                for b in b_n:
                    for r in R_n:
                        space.append([[1,b],[1,b],r])       
                para_space=space
           
            builder = build_builder(list(calc.keys())[0], para_space, parent_pk=q['parent'], precalc_done=q['pre'], copy=False)
            running = self.submit(builder)
            c[q] = running
            self.report(running.pk,q)
            running.label = q+' _extrap_'+running.pk

        return ToContext(calc)

    def results(self):
        """Process results."""
        pass
