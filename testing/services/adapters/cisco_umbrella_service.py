import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoUmbrellaService(AdapterService):
    def __init__(self):
        super().__init__('cisco-umbrella')


@pytest.fixture(scope='module', autouse=True)
def cisco_umbrella_fixture(request):
    service = CiscoUmbrellaService()
    initialize_fixture(request, service)
    return service
