import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ObserviumService(AdapterService):
    def __init__(self):
        super().__init__('observium')


@pytest.fixture(scope='module', autouse=True)
def observium_fixture(request):
    service = ObserviumService()
    initialize_fixture(request, service)
    return service
