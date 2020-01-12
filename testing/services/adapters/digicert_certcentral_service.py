import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DigicertCertcentralService(AdapterService):
    def __init__(self):
        super().__init__('digicert-certcentral')


@pytest.fixture(scope='module', autouse=True)
def digicert_certcentral_fixture(request):
    service = DigicertCertcentralService()
    initialize_fixture(request, service)
    return service
