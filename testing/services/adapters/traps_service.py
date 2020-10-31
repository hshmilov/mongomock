import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TrapsService(AdapterService):
    def __init__(self):
        super().__init__('traps')


@pytest.fixture(scope='module', autouse=True)
def traps_fixture(request):
    service = TrapsService()
    initialize_fixture(request, service)
    return service
