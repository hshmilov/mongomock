import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LogicmonitorService(AdapterService):
    def __init__(self):
        super().__init__('logicmonitor')


@pytest.fixture(scope='module', autouse=True)
def logicmonitor_fixture(request):
    service = LogicmonitorService()
    initialize_fixture(request, service)
    return service
