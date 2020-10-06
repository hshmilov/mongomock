import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DellOmeService(AdapterService):
    def __init__(self):
        super().__init__('dell-ome')


@pytest.fixture(scope='module', autouse=True)
def dell_ome_fixture(request):
    service = DellOmeService()
    initialize_fixture(request, service)
    return service
