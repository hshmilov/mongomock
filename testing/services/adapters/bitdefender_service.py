import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BitdefenderService(AdapterService):
    def __init__(self):
        super().__init__('bitdefender')


@pytest.fixture(scope='module', autouse=True)
def bitdefender_fixture(request):
    service = BitdefenderService()
    initialize_fixture(request, service)
    return service
