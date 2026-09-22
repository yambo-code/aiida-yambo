# -*- coding: utf-8 -*-
"""Test how `YamboRestart._handle_parallelism_error` answers each PARA_ERROR.

yambo reports two different parallelism failures. "USER parallel structure does
not fit the current run parameters" says the explicit `*_CPU`/`*_ROLEs` split
left a rank with nothing to do. "Impossible to define an appropriate parallel
structure" fires when yambo has discarded a split whose product does not match
the rank count and proposed its own; the error comes from that proposal, so
dropping the split cannot change the outcome and only the rank count can. The
split is left in place because it is inert at that rank count, and takes
effect again if the halved count matches its product.

This module has no AiiDA profile available, so it does not go through a real
`WorkChain` instance or `BaseRestartWorkChain` engine machinery. It calls the
handler's undecorated function (`.__wrapped__`, exposed by the `wrapt`-based
`@process_handler` decorator) directly against a minimal stand-in for `self`
and the failed calculation, and records what is handed to `update_dict`, which
needs a backend-bound `orm.Dict`. That means these tests exercise the retry the
handler prepares and nothing about handler dispatch or `update_dict` itself.
"""
from types import SimpleNamespace

import pytest

from aiida_yambo.parsers.utils import parse_log
from aiida_yambo.workflows import yamborestart as yamborestart_module
from aiida_yambo.workflows.yamborestart import YamboRestart


class _FakeCalculation:
    """Stand-in for a `YamboCalculation` that stopped on a parallelism error.

    `reason=None` stands for a calculation parsed by an earlier version of
    `parse_log`, before it recorded which parallelism message fired: its
    `output_parameters` carries no `errors` key at all.
    """

    def __init__(self, reason):
        self.inputs = SimpleNamespace(
            parameters=SimpleNamespace(get_dict=lambda: {
                'variables': {'BS_CPU': '1.1.4.1', 'BS_ROLEs': 'k.eh.t.p', 'BSENGBlk': [2.0, 'Ry']},
            }),
        )
        output_params = {'yambo_wrote_dbs': False, 'para_error': True}
        if reason is not None:
            output_params['errors'] = [reason]
        self.outputs = SimpleNamespace(
            output_parameters=SimpleNamespace(get_dict=lambda: output_params),
        )
        self.exit_status = 504


def _make_fake_self(mpiprocs_per_machine, num_machines=1):
    """Build a minimal stand-in for the `YamboRestart` instance."""
    options = SimpleNamespace(
        resources={
            'num_machines': num_machines,
            'num_mpiprocs_per_machine': mpiprocs_per_machine,
            'num_cores_per_mpiproc': 1,
        },
        prepend_text='',
    )
    ctx_inputs = SimpleNamespace(metadata=SimpleNamespace(options=options), parameters=None, settings=None)
    return SimpleNamespace(
        ctx=SimpleNamespace(inputs=ctx_inputs, iteration=1),
        inputs=SimpleNamespace(max_number_of_nodes=1),
        exit_codes=YamboRestart.exit_codes,
        report_error_handled=lambda calculation, message: reports.append(message),
    )


reports = []


@pytest.fixture(autouse=True)
def _record_update_dict(monkeypatch):
    """Record the retry `update_dict` is asked to build, and bypass it.

    `update_dict` needs a backend-bound `orm.Dict`; every line under test runs
    before its return value is used for anything but the next call.
    """
    reports.clear()
    calls.clear()
    monkeypatch.setattr(
        yamborestart_module,
        'update_dict',
        lambda _dict, whats, hows=None, sublevel=None, pop_list=None:
            calls.append({'whats': whats, 'hows': hows, 'pop_list': pop_list}) or _dict,
    )


calls = []


def _handle(fake_self, calculation):
    return YamboRestart._handle_parallelism_error.__wrapped__(fake_self, calculation)


@pytest.mark.parametrize('message, reason', (
    ('<---> P1: [ERROR] USER parallel structure does not fit the current run parameters', 'para_error_user'),
    ('<---> P1: [ERROR]Impossible to define an appropriate parallel structure', 'para_error_auto'),
))
def test_the_two_parallelism_failures_are_told_apart(message, reason):
    """Both messages stop the run, and each says which one it was."""
    output_params = {'errors': [], 'timing': [], 'para_error': False, 'game_over': False}

    parse_log(SimpleNamespace(filename='l-aiida.out', lines=[message]), output_params, timing=False)

    assert output_params['para_error'] is True
    assert output_params['errors'] == [reason]


def test_automatic_structure_failure_lowers_the_rank_count():
    """The retry after yambo's own proposal failed runs fewer ranks."""
    fake_self = _make_fake_self(mpiprocs_per_machine=4)

    _handle(fake_self, _FakeCalculation('para_error_auto'))

    assert fake_self.ctx.inputs.metadata.options.resources['num_mpiprocs_per_machine'] == 2
    assert fake_self.ctx.inputs.metadata.options.resources['num_cores_per_mpiproc'] == 2
    assert all(not call['pop_list'] for call in calls)


def test_user_split_failure_keeps_popping_the_split():
    """A split that does not fit is still dropped, at the same rank count."""
    fake_self = _make_fake_self(mpiprocs_per_machine=4)

    _handle(fake_self, _FakeCalculation('para_error_user'))

    assert fake_self.ctx.inputs.metadata.options.resources['num_mpiprocs_per_machine'] == 4
    assert calls[0]['pop_list'] == ['BS_CPU', 'BS_ROLEs']
    assert calls[0]['whats'] == ['PAR_def_mode']


def test_one_rank_per_machine_stops_instead_of_repeating_the_run():
    """With nothing left to lower, the handler gives up and says what to set."""
    fake_self = _make_fake_self(mpiprocs_per_machine=1, num_machines=4)

    report = _handle(fake_self, _FakeCalculation('para_error_auto'))

    assert report.exit_code == YamboRestart.exit_codes.ERROR_UNRECOVERABLE_FAILURE
    assert fake_self.ctx.inputs.metadata.options.resources['num_mpiprocs_per_machine'] == 1
    assert '*_CPU/*_ROLEs' in reports[0]
    assert '4 ranks' in reports[0]


def test_a_calculation_with_no_errors_key_is_handled_as_before():
    """A calculation parsed before this patch existed still pops the split."""
    fake_self = _make_fake_self(mpiprocs_per_machine=4)

    report = _handle(fake_self, _FakeCalculation(None))

    assert fake_self.ctx.inputs.metadata.options.resources['num_mpiprocs_per_machine'] == 4
    assert calls[0]['pop_list'] == ['BS_CPU', 'BS_ROLEs']
    assert report.exit_code.status == 0
