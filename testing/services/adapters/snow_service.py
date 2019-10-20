import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SnowService(AdapterService):
    def __init__(self):
        super().__init__('snow')


@pytest.fixture(scope='module', autouse=True)
def snow_fixture(request):
    service = SnowService()
    initialize_fixture(request, service)
    return service
