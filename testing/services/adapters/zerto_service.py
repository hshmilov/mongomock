import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ZertoService(AdapterService):
    def __init__(self):
        super().__init__('zerto')


@pytest.fixture(scope='module', autouse=True)
def zerto_fixture(request):
    service = ZertoService()
    initialize_fixture(request, service)
    return service
