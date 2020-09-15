import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AwakeService(AdapterService):
    def __init__(self):
        super().__init__('awake')


@pytest.fixture(scope='module', autouse=True)
def awake_fixture(request):
    service = AwakeService()
    initialize_fixture(request, service)
    return service
