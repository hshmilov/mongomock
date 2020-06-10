import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FiremonService(AdapterService):
    def __init__(self):
        super().__init__('firemon')


@pytest.fixture(scope='module', autouse=True)
def firemon_fixture(request):
    service = FiremonService()
    initialize_fixture(request, service)
    return service
