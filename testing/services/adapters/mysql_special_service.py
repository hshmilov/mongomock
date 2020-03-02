import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MysqlSpecialService(AdapterService):
    def __init__(self):
        super().__init__('mysql-special')


@pytest.fixture(scope='module', autouse=True)
def mysql_special_fixture(request):
    service = MysqlSpecialService()
    initialize_fixture(request, service)
    return service
