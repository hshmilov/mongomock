import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecEdrService(AdapterService):
    def __init__(self):
        super().__init__('symantec-edr')


@pytest.fixture(scope='module', autouse=True)
def symantec_edr_fixture(request):
    service = SymantecEdrService()
    initialize_fixture(request, service)
    return service
