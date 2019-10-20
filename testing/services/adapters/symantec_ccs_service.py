import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecCcsService(AdapterService):
    def __init__(self):
        super().__init__('symantec-ccs')


@pytest.fixture(scope='module', autouse=True)
def symantec_ccs_fixture(request):
    service = SymantecCcsService()
    initialize_fixture(request, service)
    return service
