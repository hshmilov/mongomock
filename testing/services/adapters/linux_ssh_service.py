import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LinuxSshService(AdapterService):
    def __init__(self):
        super().__init__('linux-ssh')


@pytest.fixture(scope='module', autouse=True)
def linux_ssh_fixture(request):
    service = LinuxSshService()
    initialize_fixture(request, service)
    return service
