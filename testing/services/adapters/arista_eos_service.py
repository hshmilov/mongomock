import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AristaEosService(AdapterService):
    def __init__(self):
        super().__init__('arista-eos')


@pytest.fixture(scope='module', autouse=True)
def arista_eos_fixture(request):
    service = AristaEosService()
    initialize_fixture(request, service)
    return service
