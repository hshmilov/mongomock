import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AutomoxService(AdapterService):
    def __init__(self):
        super().__init__('automox')


@pytest.fixture(scope='module', autouse=True)
def automox_fixture(request):
    service = AutomoxService()
    initialize_fixture(request, service)
    return service
