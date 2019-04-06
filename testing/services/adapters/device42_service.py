import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Device42Service(AdapterService):
    def __init__(self):
        super().__init__('device42')


@pytest.fixture(scope='module', autouse=True)
def device42_fixture(request):
    service = Device42Service()
    initialize_fixture(request, service)
    return service
