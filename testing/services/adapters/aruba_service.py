import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ArubaService(AdapterService):
    def __init__(self):
        super().__init__('aruba')


@pytest.fixture(scope='module', autouse=True)
def aruba_fixture(request):
    service = ArubaService()
    initialize_fixture(request, service)
    return service
