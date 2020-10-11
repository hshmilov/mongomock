import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NetiqService(AdapterService):
    def __init__(self):
        super().__init__('netiq')


@pytest.fixture(scope='module', autouse=True)
def netiq_fixture(request):
    service = NetiqService()
    initialize_fixture(request, service)
    return service
