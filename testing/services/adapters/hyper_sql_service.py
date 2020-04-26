import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HyperSqlService(AdapterService):
    def __init__(self):
        super().__init__('hyper-sql')


@pytest.fixture(scope='module', autouse=True)
def hyper_sql_fixture(request):
    service = HyperSqlService()
    initialize_fixture(request, service)
    return service
