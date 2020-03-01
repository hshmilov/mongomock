import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DigicertPkiPlatformService(AdapterService):
    def __init__(self):
        super().__init__('digicert-pki-platform')


@pytest.fixture(scope='module', autouse=True)
def digicert_pki_platform_fixture(request):
    service = DigicertPkiPlatformService()
    initialize_fixture(request, service)
    return service
