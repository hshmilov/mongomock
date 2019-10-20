import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CaSpectrumService(AdapterService):
    def __init__(self):
        super().__init__('ca-spectrum')


@pytest.fixture(scope='module', autouse=True)
def ca_spectrum_fixture(request):
    service = CaSpectrumService()
    initialize_fixture(request, service)
    return service
