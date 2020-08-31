import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IvantiSecurityControlsService(AdapterService):
    def __init__(self):
        super().__init__('ivanti-security-controls')


@pytest.fixture(scope='module', autouse=True)
def ivanti_security_controls_fixture(request):
    service = IvantiSecurityControlsService()
    initialize_fixture(request, service)
    return service
