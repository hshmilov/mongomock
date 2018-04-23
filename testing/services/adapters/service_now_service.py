import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ServiceNowService(AdapterService):
    def __init__(self):
        super().__init__('service-now')


@pytest.fixture(scope="module", autouse=True)
def service_now_fixture(request):
    service = ServiceNowService()
    initialize_fixture(request, service)
    return service
