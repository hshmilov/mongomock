import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DeepSecurityService(AdapterService):
    def __init__(self):
        super().__init__('deep-security')


@pytest.fixture(scope='module', autouse=True)
def deep_security_fixture(request):
    service = DeepSecurityService()
    initialize_fixture(request, service)
    return service
