#!/usr/bin/env python
"""Run a ``YamboConvergence`` with automated protocols.

Usage: verdi run example_07.py --protocol <protocol> --structure_pk <structure pk> --run yes/no
"""
import argparse
import pprint

from aiida import orm
from aiida.engine import submit
from aiida_yambo.workflows.yamboconvergence import YamboConvergence

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
    """Submit a ``YamboConvergence``."""
    # pylint: disable=import-outside-toplevel,too-many-locals

    structure = orm.load_node(options['structure_pk'])  # Si
    
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

    overrides_yambo = {}

    overrides = {
        "ywfl": {"scf": overrides_scf, "nscf": overrides_nscf, "yres": overrides_yambo}
    }

    builder = YamboConvergence.get_builder_from_protocol(
        pw_code,
        preprocessing_code,
        code,
        protocol=options['protocol'],
        structure=structure,
        overrides=overrides,
    )

    # The gaps that you want to parse
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

    pprint.pprint(builder["ywfl"]["yres"]["yambo"]['parameters'].get_dict())

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
        run.label = 'YamboConvergence test'
        print("Submitted YamboConvergence with pk=< {} >".format(run.pk))
