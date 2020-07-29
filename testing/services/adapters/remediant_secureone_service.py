import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RemediantSecureoneService(AdapterService):
    def __init__(self):
        super().__init__('remediant-secureone')


@pytest.fixture(scope='module', autouse=True)
def remediant_secureone_fixture(request):
    service = RemediantSecureoneService()
    initialize_fixture(request, service)
    return service
