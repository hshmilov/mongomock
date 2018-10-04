import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CynetService(AdapterService):
    def __init__(self):
        super().__init__('cynet')


@pytest.fixture(scope='module', autouse=True)
def cynet_fixture(request):
    service = CynetService()
    initialize_fixture(request, service)
    return service
