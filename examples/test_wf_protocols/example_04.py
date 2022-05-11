#!/usr/bin/env python
"""Launch a ``YppRestart``.

Usage: ./example_04.py
"""
import click

from aiida import cmdline, orm

from aiida_wannier90_workflows.cli.params import RUN
from aiida_wannier90_workflows.utils.workflows.builder import (
    print_builder,
    submit_and_add_group,
)


def submit(group: orm.Group = None, run: bool = False):
    """Submit a ``YppRestart``."""
    # pylint: disable=import-outside-toplevel
    from aiida_yambo.workflows.ypprestart import YppRestart

    # I need to use the seekpath-reduced primitive structure
    yambo_wkchain = orm.load_node(140260)  # Si
    parent_folder = yambo_wkchain.outputs.remote_folder
    qb_db = yambo_wkchain.outputs.QP_db

    code = orm.load_code("yambo-5.0-ypp@prnmarvelcompute5")

    builder = YppRestart.get_builder_from_protocol(
        code,
        protocol="Wannier",
        # overrides=overrides,
        parent_folder=parent_folder,
    )

    # Need nnkp file
    w90_wkchain = orm.load_node(140073)  # Si
    nnkp = w90_wkchain.outputs.wannier90_pp.nnkp_file

    builder["ypp"]["nnkp_file"] = nnkp
    builder["ypp"]["QP_DB"] = qb_db

    print_builder(builder)

    if run:
        submit_and_add_group(builder, group)


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.GROUP(
    help="The group to add the submitted workchain.",
)
@RUN()
def cli(group, run):
    """Run a ``YppRestart``."""
    submit(group, run)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
