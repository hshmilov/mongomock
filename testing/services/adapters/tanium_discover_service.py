import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TaniumDiscoverService(AdapterService):
    def __init__(self):
        super().__init__('tanium-discover')


@pytest.fixture(scope='module', autouse=True)
def tanium_discover_fixture(request):
    service = TaniumDiscoverService()
    initialize_fixture(request, service)
    return service
