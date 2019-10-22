import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AirwaveService(AdapterService):
    def __init__(self):
        super().__init__('airwave')


@pytest.fixture(scope='module', autouse=True)
def airwave_fixture(request):
    service = AirwaveService()
    initialize_fixture(request, service)
    return service
