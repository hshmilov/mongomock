import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BitlockerService(AdapterService):
    def __init__(self):
        super().__init__('bitlocker')


@pytest.fixture(scope='module', autouse=True)
def bitlocker_fixture(request):
    service = BitlockerService()
    initialize_fixture(request, service)
    return service
