import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class InfinipointService(AdapterService):
    def __init__(self):
        super().__init__('infinipoint')


@pytest.fixture(scope='module', autouse=True)
def infinipoint_fixture(request):
    service = InfinipointService()
    initialize_fixture(request, service)
    return service
