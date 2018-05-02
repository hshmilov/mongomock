import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoMerakiService(AdapterService):
    def __init__(self):
        super().__init__('cisco-meraki')


@pytest.fixture(scope="module", autouse=True)
def cisco_meraki_fixture(request):
    service = CiscoMerakiService()
    initialize_fixture(request, service)
    return service
