import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoAmpService(AdapterService):
    def __init__(self):
        super().__init__('cisco-amp')


@pytest.fixture(scope='module', autouse=True)
def cisco_amp_fixture(request):
    service = CiscoAmpService()
    initialize_fixture(request, service)
    return service
