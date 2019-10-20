import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PkwareService(AdapterService):
    def __init__(self):
        super().__init__('pkware')


@pytest.fixture(scope='module', autouse=True)
def pkware_fixture(request):
    service = PkwareService()
    initialize_fixture(request, service)
    return service
