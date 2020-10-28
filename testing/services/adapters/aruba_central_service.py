import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ArubaCentralService(AdapterService):
    def __init__(self):
        super().__init__('aruba-central')


@pytest.fixture(scope='module', autouse=True)
def aruba_central_fixture(request):
    service = ArubaCentralService()
    initialize_fixture(request, service)
    return service
