# -*- coding: utf-8 -*-
"""Regression test for `YamboRestart._handle_parallelism_error`/`_handle_memory_error`.

These handlers append an `OMP_NUM_THREADS` prepend-text line built from
`new_resources['num_cores_per_mpiproc']`. `fix_parallelism`/`fix_memory` pass
the caller's `resources` dict straight through, so on a scheduler whose
resource class carries no `num_cores_per_mpiproc` field (e.g. an AiiDA
`hyperqueue` computer), the bare subscript raises `KeyError` and the handler
never reaches its actual job of adjusting the parallelism namelist and
retrying.

This module has no AiiDA profile available, so it does not go through a real
`WorkChain` instance or `BaseRestartWorkChain` engine machinery. It calls the
handler's undecorated function (`.__wrapped__`, exposed by the `wrapt`-based
`@process_handler` decorator) directly against a minimal stand-in for `self`
and the failed calculation, and stubs out `update_dict` (which needs a
backend-bound `orm.Dict`) since it sits downstream of the line under test.
That means this test exercises exactly the `OMP_NUM_THREADS` line and
nothing about `BaseRestartWorkChain`'s handler dispatch or the rest of
`update_dict`'s behaviour.
"""
from types import SimpleNamespace

import pytest

from aiida_yambo.workflows import yamborestart as yamborestart_module
from aiida_yambo.workflows.utils.helpers_yamborestart import fix_memory
from aiida_yambo.workflows.yamborestart import YamboRestart


class _FakeCalculation:
    """Stand-in for the failed `YamboCalculation` node."""

    def __init__(self, wrote_dbs=False, has_gpu=False):
        self.inputs = SimpleNamespace(
            parameters=SimpleNamespace(get_dict=lambda: {'variables': {}}),
        )
        self.outputs = SimpleNamespace(
            output_parameters=SimpleNamespace(
                get_dict=lambda: {'yambo_wrote_dbs': wrote_dbs, 'has_gpu': has_gpu},
            ),
        )
        self.exit_status = 500


def _make_fake_self(resources, max_number_of_nodes=1):
    """Build a minimal stand-in for the `YamboRestart` instance."""
    options = SimpleNamespace(resources=dict(resources), prepend_text='')
    metadata = SimpleNamespace(options=options)
    ctx_inputs = SimpleNamespace(metadata=metadata, parameters=None, parent_folder=None, settings=None)
    ctx = SimpleNamespace(inputs=ctx_inputs, iteration=1)
    return SimpleNamespace(
        ctx=ctx,
        inputs=SimpleNamespace(max_number_of_nodes=max_number_of_nodes),
        report_error_handled=lambda calculation, message: None,
    )


@pytest.fixture(autouse=True)
def _stub_update_dict(monkeypatch):
    """Bypass `update_dict`, which needs a backend-bound `orm.Dict`.

    The line under test runs before `update_dict` is ever called, so
    stubbing it does not touch the behaviour this test exercises.
    """
    monkeypatch.setattr(yamborestart_module, 'update_dict', lambda _dict, *args, **kwargs: _dict)


def test_parallelism_handler_defaults_omp_threads_when_key_absent():
    """The fixed handler falls back to 1 OMP thread instead of raising."""
    handler = YamboRestart._handle_parallelism_error.__wrapped__
    fake_self = _make_fake_self(resources={'num_machines': 1, 'num_mpiprocs_per_machine': 1})
    calculation = _FakeCalculation(wrote_dbs=False)

    handler(fake_self, calculation)

    assert fake_self.ctx.inputs.metadata.options.prepend_text == '\nexport OMP_NUM_THREADS=1'


def test_memory_handler_defaults_omp_threads_when_key_absent():
    """The fixed handler falls back to 1 OMP thread instead of raising."""
    handler = YamboRestart._handle_memory_error.__wrapped__
    fake_self = _make_fake_self(resources={'num_machines': 1, 'num_mpiprocs_per_machine': 1})
    calculation = _FakeCalculation(wrote_dbs=False)

    handler(fake_self, calculation)

    assert fake_self.ctx.inputs.metadata.options.prepend_text == '\nexport OMP_NUM_THREADS=1'


def test_fix_memory_defaults_cores_per_mpiproc_when_key_absent():
    """`fix_memory` itself falls back to 1 core/rank before doubling it.

    A caller whose `resources` carries `num_mpiprocs_per_machine` but no
    `num_cores_per_mpiproc` (the shape AiiDA's `NodeNumberJobResource`
    leaves behind when that optional field is never set) must not raise
    `KeyError` when the memory handler halves the rank count and doubles
    the thread count per rank.
    """
    resources = {'num_machines': 1, 'num_mpiprocs_per_machine': 2}
    calculation = _FakeCalculation(wrote_dbs=False, has_gpu=False)

    _, new_resources, _ = fix_memory(resources, calculation, calculation.exit_status, max_nodes=1, iteration=1)

    assert new_resources['num_cores_per_mpiproc'] == 2
    assert new_resources['num_mpiprocs_per_machine'] == 1
