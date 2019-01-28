import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MssqlService(AdapterService):
    def __init__(self):
        super().__init__('mssql')


@pytest.fixture(scope='module', autouse=True)
def mssql_fixture(request):
    service = MssqlService()
    initialize_fixture(request, service)
    return service
