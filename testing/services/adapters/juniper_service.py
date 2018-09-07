import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JuniperService(AdapterService):
    def __init__(self):
        super().__init__('juniper')


@pytest.fixture(scope='module', autouse=True)
def juniper_fixture(request):
    service = JuniperService()
    initialize_fixture(request, service)
    return service
