import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NetAppService(AdapterService):
    def __init__(self):
        super().__init__('net-app')


@pytest.fixture(scope='module', autouse=True)
def net_app_fixture(request):
    service = NetAppService()
    initialize_fixture(request, service)
    return service
