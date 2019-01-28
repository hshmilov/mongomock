import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ProxmoxService(AdapterService):
    def __init__(self):
        super().__init__('proxmox')


@pytest.fixture(scope='module', autouse=True)
def proxmox_fixture(request):
    service = ProxmoxService()
    initialize_fixture(request, service)
    return service
