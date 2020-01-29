import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WsusService(AdapterService):
    def __init__(self):
        super().__init__('wsus')


@pytest.fixture(scope='module', autouse=True)
def wsus_fixture(request):
    service = WsusService()
    initialize_fixture(request, service)
    return service
