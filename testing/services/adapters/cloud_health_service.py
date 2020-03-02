import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CloudHealthService(AdapterService):
    def __init__(self):
        super().__init__('cloud-health')


@pytest.fixture(scope='module', autouse=True)
def cloud_health_fixture(request):
    service = CloudHealthService()
    initialize_fixture(request, service)
    return service
