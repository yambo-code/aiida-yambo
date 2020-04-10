# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import click
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import gridspec
import json
import sys
from aiida_yambo.commands.utils import command
from aiida_yambo.commands import options
import os


def get_extremes(mn, mx, mn_state, mx_state):
    if mx_state == None:
        mx_state = mx
    if mn_state == None:
        mn_state = mn
    if mn < mn_state:
        mn_state = mn
    if mx > mx_state:
        mx_state = mx
    return mx_state, mn_state


def plotter(fig, gs, ax1, ind, dep, var):
    print(("ind {}   dep {}   var {}".format(ind, dep, var)))
    ax1.plot(ind, dep, label=var, marker='+')


def read_intp_out(jsondata, legendpos, label, output="fullconv"):
    fig = plt.figure()
    gs = gridspec.GridSpec(1, 1)
    gs.update(wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
    full_result = jsondata

    max_dependent = None
    min_dependent = None
    independent_ax = np.arange(1)
    for data in full_result['ordered_step_output']:
        if "kpoints" in list(data["convergence_space"].keys()):
            dep_kp = np.array(data['energy_widths'])
            indep_kp = np.array(data['convergence_space']['kpoints'])
            indep_kp = 1.0 / indep_kp
            independent_ax = np.arange(0, indep_kp.size)
            plotter(fig, gs, ax1, independent_ax, dep_kp, "kpoints")
            mx = np.amax(dep_kp)
            mn = np.amin(dep_kp)
            min_dependent, max_dependent = get_extremes(
                mn, mx, min_dependent, max_dependent)

        if "FFTGvecs" in list(data["convergence_space"].keys()):
            indep_fft = np.array(data['convergence_space']['FFTGvecs'])
            mn, mx = indep_fft[0], indep_fft[-1]
            dep_fft = np.array(data['energy_widths'])
            independent_ax = np.arange(independent_ax[-1],
                                       independent_ax[-1] + indep_fft.size)
            plotter(fig, gs, ax1, independent_ax, dep_fft,
                    "FFT {}-{} Ry".format(mn, mx))
            mx = np.amax(dep_fft)
            mn = np.amin(dep_fft)
            min_dependent, max_dependent = get_extremes(
                mn, mx, min_dependent, max_dependent)

        if "GbndRnge" in list(data["convergence_space"].keys()):
            indep_bands = np.array(
                [el[-1] for el in data['convergence_space']['GbndRnge']])
            mn, mx = indep_bands[0], indep_bands[-1]
            dep_bands = np.array(data['energy_widths'])
            independent_ax = np.arange(
                independent_ax[-1],
                independent_ax[-1] + np.unique(indep_bands).size)
            plotter(fig, gs, ax1, independent_ax, dep_bands,
                    "Bands (1-{})-(1-{})".format(mn, mx))
            mx = np.amax(dep_bands)
            mn = np.amin(dep_bands)
            min_dependent, max_dependent = get_extremes(
                mn, mx, min_dependent, max_dependent)

        if "NGsBlkXp" in list(data["convergence_space"].keys()):
            indep_G = np.array(data['convergence_space']['NGsBlkXp'])
            mn, mx = indep_G[0], indep_G[-1]
            dep_G = np.array(data['energy_widths'])
            independent_ax = np.arange(independent_ax[-1],
                                       independent_ax[-1] + indep_G.size)
            plotter(fig, gs, ax1, independent_ax, dep_G, "W {}-{} Ry".format(
                mn, mx))
            mx = np.amax(dep_G)
            mn = np.amin(dep_G)
            min_dependent, max_dependent = get_extremes(
                mn, mx, min_dependent, max_dependent)

    h, l = ax1.get_legend_handles_labels()
    ax1.legend(h, l, loc=legendpos, ncol=1, prop={'size': 12})
    ax1.set_ylabel("Energy (eV)")
    ax1.set_xlabel('Convergence space')
    #fig.suptitle(r'Direct Gap at $\Gamma$', size=14)
    fig.suptitle(r'{}'.format(label), size=14)

    plt.xticks([], [])
    print((min_dependent * 0.7, max_dependent * 1.5))
    plt.ylim(min_dependent * 0.7, max_dependent * 1.5)
    plt.xlim(0, independent_ax[-1])
    plt.savefig(output, format='eps', dpi=1200)
    plt.show()
    plt.close()
    mpl.rcParams.update(mpl.rcParamsDefault)


@command()
@options.node()
@options.legend()
@options.label()
@options.output()
def plotconv(node=None, legendpos=None, label=None, output=None):
    """
    Create a plot showing the convergence behaviour of the Full convergence workflow
    """
    plot_data = node
    read_intp_out(plot_data, legendpos, label, output)
