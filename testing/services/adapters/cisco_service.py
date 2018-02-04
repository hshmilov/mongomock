import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoService(AdapterService):
    def __init__(self):
        super().__init__('cisco')


@pytest.fixture(scope="module", autouse=True)
def cisco_fixture(request):
    service = CiscoService()
    initialize_fixture(request, service)
    return service
