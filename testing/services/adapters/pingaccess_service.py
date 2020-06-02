import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PingaccessService(AdapterService):
    def __init__(self):
        super().__init__('pingaccess')


@pytest.fixture(scope='module', autouse=True)
def pingaccess_fixture(request):
    service = PingaccessService()
    initialize_fixture(request, service)
    return service
