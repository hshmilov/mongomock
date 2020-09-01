import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class UptycsService(AdapterService):
    def __init__(self):
        super().__init__('uptycs')


@pytest.fixture(scope='module', autouse=True)
def uptycs_fixture(request):
    service = UptycsService()
    initialize_fixture(request, service)
    return service
