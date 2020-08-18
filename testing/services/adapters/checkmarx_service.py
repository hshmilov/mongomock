import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CheckmarxService(AdapterService):
    def __init__(self):
        super().__init__('checkmarx')


@pytest.fixture(scope='module', autouse=True)
def checkmarx_fixture(request):
    service = CheckmarxService()
    initialize_fixture(request, service)
    return service
