import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IllumioService(AdapterService):
    def __init__(self):
        super().__init__('illumio')


@pytest.fixture(scope='module', autouse=True)
def illumio_fixture(request):
    service = IllumioService()
    initialize_fixture(request, service)
    return service
