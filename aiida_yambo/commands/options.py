# -*- coding: utf-8 -*-
from __future__ import absolute_import
import click

import click
from aiida_yambo.commands import validators


class option(object):
    """
    """

    def __init__(self, *args, **kwargs):
        """
        """
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        """
        """
        import functools
        if not args:
            args_copy = self.args
        else:
            args_copy = args

        kw_copy = self.kwargs.copy()
        kw_copy.update(kwargs)

        # Pop the optional callback_kwargs if present
        callback_kwargs = kw_copy.pop('callback_kwargs', {})

        if 'callback' in kw_copy:
            callback_plain = kw_copy['callback']
            callback_bound = functools.partial(callback_plain, callback_kwargs)
            kw_copy['callback'] = callback_bound

        return click.option(*args_copy, **kw_copy)


node = option(
    '-n',
    '--node',
    type=click.INT,
    required=True,
    callback=validators.validate_node,
    help='the full convergence node pk')

legend = option(
    '-lg',
    '--legendpos',
    type=click.INT,
    required=False,
    default=0,
    callback=validators.validate_legendpos,
    help=
    'the postion of the legend: 1 = upper right , 2 = upper left , 3 = lower left, 4 = lower right '
)

label = option(
    '-lb',
    '--label',
    type=click.STRING,
    required=True,
    default='Full Convergence History',
    show_default=True,
    callback=validators.validate_label,
    help='the figure label text')

output = option(
    '-o',
    '--output',
    type=click.STRING,
    required=True,
    default='output',
    show_default=True,
    callback=validators.validate_output,
    help='the output image name')
