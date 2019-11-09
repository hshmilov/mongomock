import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NutanixService(AdapterService):
    def __init__(self):
        super().__init__('nutanix')


@pytest.fixture(scope='module', autouse=True)
def nutanix_fixture(request):
    service = NutanixService()
    initialize_fixture(request, service)
    return service
