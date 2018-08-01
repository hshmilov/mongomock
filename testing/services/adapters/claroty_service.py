import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ClarotyService(AdapterService):
    def __init__(self):
        super().__init__('claroty')


@pytest.fixture(scope='module', autouse=True)
def clartoy_fixture(request):
    service = ClarotyService()
    initialize_fixture(request, service)
    return service
