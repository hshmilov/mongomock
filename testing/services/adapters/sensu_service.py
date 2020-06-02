import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SensuService(AdapterService):
    def __init__(self):
        super().__init__('sensu')


@pytest.fixture(scope='module', autouse=True)
def sensu_fixture(request):
    service = SensuService()
    initialize_fixture(request, service)
    return service
