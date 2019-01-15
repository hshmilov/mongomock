import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SaltstackService(AdapterService):
    def __init__(self):
        super().__init__('saltstack')


@pytest.fixture(scope='module', autouse=True)
def saltstack_fixture(request):
    service = SaltstackService()
    initialize_fixture(request, service)
    return service
