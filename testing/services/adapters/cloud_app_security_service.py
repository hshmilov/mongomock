import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CloudAppSecurityService(AdapterService):
    def __init__(self):
        super().__init__('cloud-app-security')


@pytest.fixture(scope='module', autouse=True)
def cloud_app_security_fixture(request):
    service = CloudAppSecurityService()
    initialize_fixture(request, service)
    return service
