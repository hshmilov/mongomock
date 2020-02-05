import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ArsenalService(AdapterService):
    def __init__(self):
        super().__init__('arsenal')


@pytest.fixture(scope='module', autouse=True)
def arsenal_fixture(request):
    service = ArsenalService()
    initialize_fixture(request, service)
    return service
