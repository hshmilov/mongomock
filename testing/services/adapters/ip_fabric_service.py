import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IpFabricService(AdapterService):
    def __init__(self):
        super().__init__('ip-fabric')


@pytest.fixture(scope='module', autouse=True)
def ip_fabric_fixture(request):
    service = IpFabricService()
    initialize_fixture(request, service)
    return service
