import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NetbrainService(AdapterService):
    def __init__(self):
        super().__init__('netbrain')


@pytest.fixture(scope='module', autouse=True)
def netbrain_fixture(request):
    service = NetbrainService()
    initialize_fixture(request, service)
    return service
