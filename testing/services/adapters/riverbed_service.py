import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RiverbedService(AdapterService):
    def __init__(self):
        super().__init__('riverbed')


@pytest.fixture(scope='module', autouse=True)
def riverbed_fixture(request):
    service = RiverbedService()
    initialize_fixture(request, service)
    return service
