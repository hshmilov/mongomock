import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CloudpassageService(AdapterService):
    def __init__(self):
        super().__init__('cloudpassage')


@pytest.fixture(scope='module', autouse=True)
def cloudpassage_fixture(request):
    service = CloudpassageService()
    initialize_fixture(request, service)
    return service
