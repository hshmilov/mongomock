import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GuardiumService(AdapterService):
    def __init__(self):
        super().__init__('guardium')


@pytest.fixture(scope='module', autouse=True)
def guardium_fixture(request):
    service = GuardiumService()
    initialize_fixture(request, service)
    return service
