import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ZabbixService(AdapterService):
    def __init__(self):
        super().__init__('zabbix')


@pytest.fixture(scope='module', autouse=True)
def zabbix_fixture(request):
    service = ZabbixService()
    initialize_fixture(request, service)
    return service
