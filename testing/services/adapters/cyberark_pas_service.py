import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CyberarkPasService(AdapterService):
    def __init__(self):
        super().__init__('cyberark-pas')


@pytest.fixture(scope='module', autouse=True)
def cyberark_pas_fixture(request):
    service = CyberarkPasService()
    initialize_fixture(request, service)
    return service
