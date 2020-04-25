import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ExtraHopService(AdapterService):
    def __init__(self):
        super().__init__('extra-hop')


@pytest.fixture(scope='module', autouse=True)
def extra_hop_fixture(request):
    service = ExtraHopService()
    initialize_fixture(request, service)
    return service
