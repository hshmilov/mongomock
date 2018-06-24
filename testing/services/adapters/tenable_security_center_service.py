import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TenableSecurityCenterService(AdapterService):
    def __init__(self):
        super().__init__('tenable-security-center')


@pytest.fixture(scope="module", autouse=True)
def tenable_security_center_fixture(request):
    service = TenableSecurityCenterService()
    initialize_fixture(request, service)
    return service
