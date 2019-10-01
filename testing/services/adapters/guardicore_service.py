import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GuardicoreService(AdapterService):
    def __init__(self):
        super().__init__('guardicore')


@pytest.fixture(scope='module', autouse=True)
def guardicore_fixture(request):
    service = GuardicoreService()
    initialize_fixture(request, service)
    return service
