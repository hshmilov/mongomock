import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PingoneService(AdapterService):
    def __init__(self):
        super().__init__('pingone')


@pytest.fixture(scope='module', autouse=True)
def pingone_fixture(request):
    service = PingoneService()
    initialize_fixture(request, service)
    return service
