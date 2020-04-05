# -*- coding: utf-8 -*-
from __future__ import absolute_import
import click
import os
from six.moves import range


def validate_node(callback_kwargs, ctx, param, value):
    """
    """
    from aiida.common.exceptions import NotExistent, LoadingPluginFailed, MissingPluginError
    from aiida.orm import load_node
    from aiida.orm.implementation.general.calculation.work import WorkCalculation

    try:
        worknode = load_node(int(value))
    except NotExistent as exception:
        raise click.BadParameter('failed to load the node<{}>\n{}'.format(
            value, exception))

    if not isinstance(worknode, WorkCalculation):
        raise click.BadParameter('node<{}> is not of type {}'.format(
            value, WorkCalculation.__name__))

    try:
        plotdata = worknode.get_outputs_dict()['result'].get_dict()
    except KeyError as exception:
        raise click.BadParameter(
            'Node {} does node have result key:  {}, FullConvergence workflow may not have successfully completed'
            .format(value, exception))

    return plotdata


def validate_legendpos(callback_kwargs, ctx, param, value):
    """
     1 = upper right , 2 = upper left , 3 = lower left, 4 = lower right, 
    """
    from aiida.common.exceptions import NotExistent, LoadingPluginFailed, MissingPluginError
    if value not in list(range(0, 11)):
        raise click.BadParameter(
            'Legend position needs to be in range [0-10]'.format(value))

    return value


def validate_label(callback_kwargs, ctx, param, value):
    """
    """
    from aiida.common.exceptions import NotExistent, LoadingPluginFailed, MissingPluginError

    return value


def validate_output(callback_kwargs, ctx, param, value):
    """
    """
    from aiida.common.exceptions import NotExistent, LoadingPluginFailed, MissingPluginError
    value = os.path.splitext(value)[0] + '.eps'
    return value
