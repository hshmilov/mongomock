import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NmapService(AdapterService):
    def __init__(self):
        super().__init__('nmap')


@pytest.fixture(scope='module', autouse=True)
def nmap_fixture(request):
    service = NmapService()
    initialize_fixture(request, service)
    return service
