#!/usr/bin/env python
"""Run a ``YamboConvergence``.

Usage: ./example_07.py
"""
import click

from aiida import cmdline, orm

from aiida_wannier90_workflows.cli.params import RUN
from aiida_wannier90_workflows.utils.workflows.builder import (
    print_builder,
    submit_and_add_group,
)


def submit(group: orm.Group = None, run: bool = False):
    """Submit a ``YamboConvergence``."""
    # pylint: disable=import-outside-toplevel,too-many-locals
    from aiida_yambo.workflows.yamboconvergence import YamboConvergence

    w90_wkchain = orm.load_node(140073)  # Si
    structure = w90_wkchain.outputs.primitive_structure

    # pw_code = 'qe-git-pw@localhost'
    # preprocessing_code = 'yambo-5.0-p2y@localhost'
    # code = 'yambo-5.0-yambo@localhost'
    pw_code = "qe-git-pw@prnmarvelcompute5"
    preprocessing_code = "yambo-5.0-p2y@prnmarvelcompute5"
    code = "yambo-5.0-yambo@prnmarvelcompute5"

    pw_code = orm.load_code(pw_code)
    preprocessing_code = orm.load_code(preprocessing_code)
    code = orm.load_code(code)

    ecutwfc = 80
    pseudo_family = "PseudoDojo/0.4/PBE/SR/standard/upf"
    parallelization = {"npool": 8}

    overrides_scf = {
        "pseudo_family": pseudo_family,
        "pw": {
            "parameters": {
                "SYSTEM": {
                    "ecutwfc": ecutwfc,
                },
            },
            "parallelization": parallelization,
        },
    }

    overrides_nscf = {
        "pseudo_family": pseudo_family,
        "pw": {
            "parameters": {
                "SYSTEM": {
                    "ecutwfc": ecutwfc,
                },
            },
            "parallelization": parallelization,
        },
    }

    overrides_yambo = {
        "yambo": {
            "parameters": {
                "arguments": [
                    "rim_cut",
                ],
                "variables": {
                    "NGsBlkXp": [4, "Ry"],
                    "BndsRnXp": [[1, 200], ""],
                    "GbndRnge": [[1, 200], ""],
                    "RandQpts": [5000000, ""],
                    "RandGvec": [100, "RL"],
                    #'X_and_IO_CPU' : '1 1 1 32 1',
                    #'X_and_IO_ROLEs' : 'q k g c v',
                    #'DIP_CPU' :'1 32 1',
                    #'DIP_ROLEs' : 'k c v',
                    #'SE_CPU' : '1 1 32',
                    #'SE_ROLEs' : 'q qp b',
                    "QPkrange": [[[1, 1, 32, 32]], ""],
                },
            },
        },
    }

    overrides = {
        "ywfl": {"scf": overrides_scf, "nscf": overrides_nscf, "yres": overrides_yambo}
    }

    builder = YamboConvergence.get_builder_from_protocol(
        pw_code,
        preprocessing_code,
        code,
        protocol="moderate",
        structure=structure,
        overrides=overrides,
    )

    # builder["ywfl"]['nscf']['kpoints'] = orm.KpointsData()
    # builder["ywl"]['nscf']['kpoints'].set_kpoints_mesh([12,12,1])

    # The gaps that you want
    builder["ywfl"]["additional_parsing"] = orm.List(
        list=[
            "gap_KK",
            "gap_MM",
            "gap_MK",
            "gap_KG",
            "gap_GG",
            "gap_",
        ]
    )

    builder.parameters_space = orm.List(
        list=[
            {
                "var": ["BndsRnXp", "GbndRnge", "NGsBlkXp"],
                "start": [100, 100, 2],
                "stop": [600, 600, 12],
                "delta": [100, 100, 2],
                "max": [1600, 1600, 36],
                "steps": 6,
                "max_iterations": 8,
                "conv_thr": 0.1,
                "conv_thr_units": "eV",
                "convergence_algorithm": "new_algorithm_2D",
            },
        ]
    )

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
    """Run a ``YamboConvergence``."""
    submit(group, run)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
