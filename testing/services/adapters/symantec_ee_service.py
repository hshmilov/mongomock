import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecEeService(AdapterService):
    def __init__(self):
        super().__init__('symantec-ee')


@pytest.fixture(scope='module', autouse=True)
def symantec_ee_fixture(request):
    service = SymantecEeService()
    initialize_fixture(request, service)
    return service
