import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NimbulService(AdapterService):
    def __init__(self):
        super().__init__('nimbul')


@pytest.fixture(scope='module', autouse=True)
def nimbul_fixture(request):
    service = NimbulService()
    initialize_fixture(request, service)
    return service
