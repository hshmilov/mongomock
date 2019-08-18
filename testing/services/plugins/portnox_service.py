import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class PortnoxService(PluginService):
    def __init__(self):
        super().__init__('portnox')


@pytest.fixture(scope='module')
def portnox_fixture(request):
    service = PortnoxService()
    initialize_fixture(request, service)
    return service
