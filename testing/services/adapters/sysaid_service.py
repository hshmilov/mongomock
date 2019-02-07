import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SysaidService(AdapterService):
    def __init__(self):
        super().__init__('sysaid')


@pytest.fixture(scope='module', autouse=True)
def sysaid_fixture(request):
    service = SysaidService()
    initialize_fixture(request, service)
    return service
