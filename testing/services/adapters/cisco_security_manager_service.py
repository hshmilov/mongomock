import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CiscoSecurityManagerService(AdapterService):
    def __init__(self):
        super().__init__('cisco-security-manager')


@pytest.fixture(scope='module', autouse=True)
def cisco_security_manager_fixture(request):
    service = CiscoSecurityManagerService()
    initialize_fixture(request, service)
    return service
