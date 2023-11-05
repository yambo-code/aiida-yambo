import pytest
pytest_plugins = ['aiida.manage.tests.pytest_fixtures']

# Example of how to define your own fixture
@pytest.fixture(scope='function', autouse=True)
def clear_database_auto(clear_database):
    """Automatically clear database in between tests."""
    pass
