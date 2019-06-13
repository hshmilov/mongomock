import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NetboxService(AdapterService):
    def __init__(self):
        super().__init__('netbox')


@pytest.fixture(scope='module', autouse=True)
def netbox_fixture(request):
    service = NetboxService()
    initialize_fixture(request, service)
    return service
