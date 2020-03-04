import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SqliteService(AdapterService):
    def __init__(self):
        super().__init__('sqlite')


@pytest.fixture(scope='module', autouse=True)
def sqlite_fixture(request):
    service = SqliteService()
    initialize_fixture(request, service)
    return service
