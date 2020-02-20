#from aiida.manage.fixtures import fixture_database, fixture_computer_localhost
import pytest
import tempfile
import shutil
from aiida.manage.fixtures import fixture_manager
pytest_plugins = ['aiida.manage.tests.pytest_fixtures'] 
@pytest.fixture(scope='session')
def fixture_work_directory():
    """Return a temporary folder that can be used as for example a computer's work directory."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)

@pytest.fixture(scope='function')
def fixture_computer_localhost(fixture_work_directory):
    """Return a `Computer` instance mocking a localhost setup."""
    from aiida.orm import Computer
    computer = Computer(
        name='localhost',
        hostname='localhost',
        transport_type='local',
        scheduler_type='direct',
        workdir=fixture_work_directory).store()
    computer.set_default_mpiprocs_per_machine(1)
    yield computer


def test_naive_parser(fixture_computer_localhost):
    example_out = {"errors": [], "warnings": [], "yambo_wrote": False}
    from aiida.orm import Dict
    exampleparam = Dict(dict=example_out)
    exampleparam.store()
    from aiida.orm import load_node
    assert load_node(exampleparam.pk)
