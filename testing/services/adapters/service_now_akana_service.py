import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ServiceNowAkanaService(AdapterService):
    def __init__(self):
        super().__init__('service-now-akana')


@pytest.fixture(scope='module', autouse=True)
def service_now_akana_fixture(request):
    service = ServiceNowAkanaService()
    initialize_fixture(request, service)
    return service
