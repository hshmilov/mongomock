import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoUcmService(AdapterService):
    def __init__(self):
        super().__init__('cisco-ucm')


@pytest.fixture(scope='module', autouse=True)
def cisco_ucm_fixture(request):
    service = CiscoUcmService()
    initialize_fixture(request, service)
    return service
