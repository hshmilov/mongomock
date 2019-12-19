import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoUcsmService(AdapterService):
    def __init__(self):
        super().__init__('cisco-ucsm')


@pytest.fixture(scope='module', autouse=True)
def cisco_ucsm_fixture(request):
    service = CiscoUcsmService()
    initialize_fixture(request, service)
    return service
