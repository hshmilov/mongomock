import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JunosService(AdapterService):
    def __init__(self):
        super().__init__('junos')


@pytest.fixture(scope="module", autouse=True)
def junos_fixture(request):
    service = JunosService()
    initialize_fixture(request, service)
    return service
