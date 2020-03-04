import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ContrastSecurityService(AdapterService):
    def __init__(self):
        super().__init__('contrast-security')


@pytest.fixture(scope='module', autouse=True)
def contrast_security_fixture(request):
    service = ContrastSecurityService()
    initialize_fixture(request, service)
    return service
