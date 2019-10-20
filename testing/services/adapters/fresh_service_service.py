import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FreshServiceService(AdapterService):
    def __init__(self):
        super().__init__('fresh-service')


@pytest.fixture(scope='module', autouse=True)
def fresh_service_fixture(request):
    service = FreshServiceService()
    initialize_fixture(request, service)
    return service
