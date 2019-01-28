import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ShodanService(AdapterService):
    def __init__(self):
        super().__init__('shodan')


@pytest.fixture(scope='module', autouse=True)
def shodan_fixture(request):
    service = ShodanService()
    initialize_fixture(request, service)
    return service
