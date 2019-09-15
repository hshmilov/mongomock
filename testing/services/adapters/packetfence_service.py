import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PacketfenceService(AdapterService):
    def __init__(self):
        super().__init__('packetfence')


@pytest.fixture(scope='module', autouse=True)
def packetfence_fixture(request):
    service = PacketfenceService()
    initialize_fixture(request, service)
    return service
