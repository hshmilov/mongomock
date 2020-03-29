import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JitaService(AdapterService):
    def __init__(self):
        super().__init__('jita')


@pytest.fixture(scope='module', autouse=True)
def jita_fixture(request):
    service = JitaService()
    initialize_fixture(request, service)
    return service
