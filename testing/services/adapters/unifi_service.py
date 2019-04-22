import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class UnifiService(AdapterService):
    def __init__(self):
        super().__init__('unifi')


@pytest.fixture(scope='module', autouse=True)
def unifi_fixture(request):
    service = UnifiService()
    initialize_fixture(request, service)
    return service
