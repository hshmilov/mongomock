import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecDcsService(AdapterService):
    def __init__(self):
        super().__init__('symantec-dcs')


@pytest.fixture(scope='module', autouse=True)
def symantec_dcs_fixture(request):
    service = SymantecDcsService()
    initialize_fixture(request, service)
    return service
