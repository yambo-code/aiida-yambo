#!/usr/bin/env python
"""Launch a ``YamboWorkflow``.

Usage: ./example_03.py
"""
import click

from aiida import cmdline, orm

from aiida_quantumespresso.workflows.pw.base import PwBaseWorkChain

from aiida_wannier90_workflows.cli.params import RUN
from aiida_wannier90_workflows.utils.kpoints import create_kpoints_from_mesh
from aiida_wannier90_workflows.utils.workflows.builder import (
    print_builder,
    set_kpoints,
    set_parallelization,
    submit_and_add_group,
)


def submit(group: orm.Group = None, run: bool = False):
    """Submit a ``YamboWorkflow``."""
    # pylint: disable=too-many-locals,import-outside-toplevel
    from aiida_yambo.workflows.yambowf import YamboWorkflow

    # I need to use the seekpath-reduced primitive structure
    w90_wkchain = orm.load_node(140073)  # Si
    structure = w90_wkchain.outputs.primitive_structure

    pw_code = orm.load_code("qe-git-pw@prnmarvelcompute5")
    preprocessing_code = orm.load_code("yambo-5.0-p2y@prnmarvelcompute5")
    code = orm.load_code("yambo-5.0-yambo@prnmarvelcompute5")

    ecutwfc = 80
    pseudo_family = "PseudoDojo/0.4/PBE/SR/standard/upf"

    overrides_scf = {
        "pseudo_family": pseudo_family,
        "pw": {
            "parameters": {
                "SYSTEM": {
                    "ecutwfc": ecutwfc,
                },
            },
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
                    # 'QPkrange': [[[1, 1, 32, 32]], ''],
                    "QPkrange": [
                        [
                            [1, 1, 1, 14],
                            [3, 3, 1, 14],
                            [5, 5, 1, 14],
                            [13, 13, 1, 14],
                            [15, 15, 1, 14],
                            [17, 17, 1, 14],
                            [21, 21, 1, 14],
                            [29, 29, 1, 14],
                        ],
                        "",
                    ],
                },
            },
        },
    }

    overrides = {"scf": overrides_scf, "nscf": overrides_nscf, "yres": overrides_yambo}

    builder = YamboWorkflow.get_builder_from_protocol(
        pw_code,
        preprocessing_code,
        code,
        protocol_qe="fast",
        protocol="fast",
        structure=structure,
        overrides=overrides,
        # parent_folder=orm.load_node(225176).outputs.remote_folder,
    )

    kpoints_nscf = create_kpoints_from_mesh(structure, [8, 8, 8])
    set_kpoints(builder.nscf, kpoints_nscf, process_class=PwBaseWorkChain)

    parallelization = {
        "npool": 8,
    }
    set_parallelization(builder.scf, parallelization, process_class=PwBaseWorkChain)
    set_parallelization(builder.nscf, parallelization, process_class=PwBaseWorkChain)

    # The gaps that you want
    # builder.additional_parsing = orm.List(
    #     list=[
    #         "gap_KK",
    #         "gap_MM",
    #         "gap_MK",
    #         "gap_KG",
    #         "gap_GG",
    #         "gap_",
    #     ]
    # )

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
    """Run a ``YamboWorkflow``."""
    submit(group, run)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
