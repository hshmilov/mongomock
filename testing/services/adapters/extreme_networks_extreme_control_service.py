import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ExtremeNetworksExtremeControlService(AdapterService):
    def __init__(self):
        super().__init__('extreme-networks-extreme-control')


@pytest.fixture(scope='module', autouse=True)
def extreme_networks_extreme_control_fixture(request):
    service = ExtremeNetworksExtremeControlService()
    initialize_fixture(request, service)
    return service
