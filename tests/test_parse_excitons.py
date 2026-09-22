# -*- coding: utf-8 -*-
"""Test how `parse_excitons` picks the lowest exciton out of a parsed BSE run.

`array_excitonic_states` carries the exciton energies in the order yambo's
diagonalization returns them. A TDA or resonant run diagonalizes a Hermitian
kernel and always gets an ascending table. A run with coupling diagonalizes
the non-Hermitian H = [[R, C], [-C*, -R*]], so the table holds all 2N
eigenvalues and half of them carry a negative real energy from the
anti-resonant branch; a run with finite lifetimes and no perturbative width
is non-Hermitian too and is not sorted either. The lowest exciton is the
minimum over the entries with positive real energy, which excludes that
negative branch in the coupling case.

The helpers module builds an `orm.Bool` at import time, so it needs a profile
before it can be imported at all; the fixture below opens a temporary sqlite
one, which needs no database server and no yambo binary. The stand-in for the
calculation serves the two arrays the function reads and nothing else, so these
tests cover the selection and nothing about the parser that fills them.
"""
import numpy as np
import pytest

from aiida.manage.configuration import profile_context
from aiida.storage.sqlite_temp import SqliteTempBackend


@pytest.fixture(scope='module')
def parse_excitons():
    """Import the helper under a throwaway profile."""
    profile = SqliteTempBackend.create_profile('yambo-parse-excitons')
    with profile_context(profile, allow_switch=True):
        from aiida_yambo.workflows.utils.helpers_yambowf import parse_excitons as helper
        yield helper


class _FakeCalculation:
    """Stand-in for a finished `YamboCalculation` with a BSE output array."""

    def __init__(self, energies, intensities):
        arrays = {'energies': np.array(energies), 'intensities': np.array(intensities)}
        self.outputs = type('outputs', (), {
            'array_excitonic_states': type('array', (), {'get_array': staticmethod(arrays.get)})(),
        })()


def test_lowest_exciton_of_an_unordered_table(parse_excitons):
    """The lowest exciton is the one with the smallest energy."""
    calc = _FakeCalculation(energies=[5.4, 2.1, 7.8], intensities=[1.0, 0.5, 0.2])

    energy, index = parse_excitons(calc, 'lowest')

    assert energy == pytest.approx(2.1)
    assert index == 2


def test_lowest_exciton_of_an_ascending_table(parse_excitons):
    """An ascending table still gives its first entry, as it always did."""
    calc = _FakeCalculation(energies=[2.1, 5.4, 7.8], intensities=[1.0, 0.5, 0.2])

    energy, index = parse_excitons(calc, 'lowest')

    assert energy == pytest.approx(2.1)
    assert index == 1


def test_lowest_exciton_of_a_coupling_table(parse_excitons):
    """A coupling run's table excludes the negative anti-resonant branch."""
    energies = [65.4, 52.2, 45.2, 18.8, 29.1, 32.9, -65.4, -18.8, -52.2, -45.2, -32.9, -29.1]
    calc = _FakeCalculation(energies=energies, intensities=[1.0] * len(energies))

    energy, index = parse_excitons(calc, 'lowest')

    assert energy == pytest.approx(18.8)
    assert index == 4
