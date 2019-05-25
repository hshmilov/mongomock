import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BitsightService(AdapterService):
    def __init__(self):
        super().__init__('bitsight')


@pytest.fixture(scope='module', autouse=True)
def bitsight_fixture(request):
    service = BitsightService()
    initialize_fixture(request, service)
    return service
