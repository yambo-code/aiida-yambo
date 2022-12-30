#!/usr/bin/env python
"""Launch a ``YamboWorkflow``.

Usage: verdi run example_03.py --protocol <protocol> --structure_pk <structure pk> --run yes/no
"""
import argparse
import pprint

from aiida import orm
from aiida.engine import submit
from aiida_yambo.workflows.yambowf import YamboWorkflow


def get_options():
    
    parser = argparse.ArgumentParser(description='YAMBO calculation.')
    
    parser.add_argument(
        '--protocol',
        type=str,
        dest='protocol',
        required=False,
        default='moderate',
        help='Yambo protocol')

    parser.add_argument(
        '--structure_pk',
        type=int,
        dest='structure_pk',
        required=True,
        help='structure pk')

    parser.add_argument(
        '--run',
        type=str,
        dest='run',
        required=False,
        default='no',
        help='run?') 
    
    args = parser.parse_args()

    options = {
        'protocol':args.protocol,
        'structure_pk':args.structure_pk,
        'run':False,
        }

    if args.run == 'yes':
        options['run'] = True

    return options

def builder_creation_and_submission(options, group: orm.Group = None, run: bool = False):
    """Submit a ``YamboWorkflow``."""
    # pylint: disable=too-many-locals,import-outside-toplevel
    from aiida_yambo.workflows.yambowf import YamboWorkflow

    structure = orm.load_node(options['structure_pk'])  # Si

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
        protocol_qe="moderate",
        protocol=options['protocol'],
        structure=structure,
        overrides=overrides,
        # parent_folder=orm.load_node(225176).outputs.remote_folder,
    )

    builder["scf"]["pw"]["parallelization"] = orm.Dict(
        dict={
            "npool": 8,
        }
    )
    builder["nscf"]["pw"]["parallelization"] = orm.Dict(
        dict={
            "npool": 8,
        }
    )

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

    pprint.pprint(builder["yres"]["yambo"]['parameters'].get_dict())

    if options['run']:
        run = submit(builder)
    else:
        run = None

    return run

if __name__ == "__main__":

    options = get_options()

    pprint.pprint(options)

    run = builder_creation_and_submission(options)  # pylint: disable=no-value-for-parameter

    if hasattr(run,'label'):
        run.label = 'YamboWorkflow test'
        print("Submitted YamboWorkflow with pk=< {} >".format(run.pk))