import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RedhatSatelliteService(AdapterService):
    def __init__(self):
        super().__init__('redhat-satellite')


@pytest.fixture(scope='module', autouse=True)
def redhat_satellite_fixture(request):
    service = RedhatSatelliteService()
    initialize_fixture(request, service)
    return service
