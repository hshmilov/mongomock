import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WmiService(AdapterService):
    def __init__(self):
        super().__init__('wmi')


@pytest.fixture(scope='module', autouse=True)
def wmi_fixture(request):
    service = WmiService()
    initialize_fixture(request, service)
    return service
