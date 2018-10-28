import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FortigateService(AdapterService):
    def __init__(self):
        super().__init__('fortigate')


@pytest.fixture(scope='module', autouse=True)
def fortigate_fixture(request):
    service = FortigateService()
    initialize_fixture(request, service)
    return service
