# -*- coding: utf-8 -*-
"""Test the retrieve list `YamboCalculation` builds for an initialisation run.

A setup run writes both `SAVE/ns.db1` and `SAVE/ndb.kindx`, or, under
`DBsFRAGpm=+QINDX`/`+ALL`, `SAVE/ndb.kindx_fragment_1` through `_4` instead.
Any later tool that builds a database against that SAVE - a QP database
written outside AiiDA, for instance - reads one of these, so it has to come
back with the retrieved folder.

This module has no AiiDA profile available, so it does not build real ORM nodes.
It calls `prepare_for_submission` against a stand-in for `self`, exercising the
`INITIALISE` branch, which writes no input file and reads no parameters. That
means the test covers the retrieve list and nothing about node validation, the
parent-folder copy logic or the non-initialisation branch.
"""
from types import SimpleNamespace

import pytest

from aiida_yambo.calculations import yambo as yambo_module
from aiida_yambo.calculations.yambo import YamboCalculation


class _FakeRemoteFolder:
    """Stand-in for the parent `RemoteData`."""

    computer = SimpleNamespace(uuid='computer-uuid')

    def get_remote_path(self):
        return '/scratch/parent'

    def get_incoming(self):
        parent = SimpleNamespace(
            process_type='aiida.calculations:quantumespresso.pw',
            outputs=SimpleNamespace(),
        )
        return SimpleNamespace(all_nodes=lambda: [parent])


def _make_fake_self(settings):
    """Build a minimal stand-in for the `YamboCalculation` instance."""
    inputs = SimpleNamespace(
        settings=SimpleNamespace(get_dict=lambda: dict(settings)),
        parameters=SimpleNamespace(get_dict=lambda: {'arguments': [], 'variables': {}}),
        parent_folder=_FakeRemoteFolder(),
        code=SimpleNamespace(uuid='code-uuid'),
        preprocessing_code=SimpleNamespace(uuid='precode-uuid'),
        precode_parameters=SimpleNamespace(get_dict=lambda: {}),
    )
    options = SimpleNamespace(input_filename='aiida.in', output_filename='aiida.out')
    return SimpleNamespace(uuid='calc-uuid', inputs=inputs, metadata=SimpleNamespace(options=options))


@pytest.fixture(autouse=True)
def _stub_take_calc_from_remote(monkeypatch):
    """Bypass the provenance walk, which needs a stored parent node."""
    monkeypatch.setattr(
        yambo_module,
        'take_calc_from_remote',
        lambda folder, level=-1: SimpleNamespace(process_type='aiida.calculations:quantumespresso.pw'),
    )


def test_initialisation_retrieves_the_setup_databases():
    """A setup run brings back the k/q indexes next to the lattice database."""
    calcinfo = YamboCalculation.prepare_for_submission(
        _make_fake_self({'INITIALISE': True}), tempfolder=None
    )

    assert 'SAVE/ns.db1' in calcinfo.retrieve_list
    assert 'SAVE/ndb.kindx*' in calcinfo.retrieve_list


def test_additional_retrieve_list_still_honoured():
    """`ADDITIONAL_RETRIEVE_LIST` keeps reaching the retrieve list."""
    calcinfo = YamboCalculation.prepare_for_submission(
        _make_fake_self({'INITIALISE': True, 'ADDITIONAL_RETRIEVE_LIST': 'SAVE/ndb.gops'}),
        tempfolder=None,
    )

    assert 'SAVE/ndb.gops' in calcinfo.retrieve_list
