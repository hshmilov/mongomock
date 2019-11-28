import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoStealthwatchService(AdapterService):
    def __init__(self):
        super().__init__('cisco-stealthwatch')


@pytest.fixture(scope='module', autouse=True)
def cisco_stealthwatch_fixture(request):
    service = CiscoStealthwatchService()
    initialize_fixture(request, service)
    return service
