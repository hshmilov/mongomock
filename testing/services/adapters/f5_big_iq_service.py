import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class F5BigIqService(AdapterService):
    def __init__(self):
        super().__init__('f5-big-iq')


@pytest.fixture(scope='module', autouse=True)
def f5_big_iq_fixture(request):
    service = F5BigIqService()
    initialize_fixture(request, service)
    return service
