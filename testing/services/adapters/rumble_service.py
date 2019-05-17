import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RumbleService(AdapterService):
    def __init__(self):
        super().__init__('rumble')


@pytest.fixture(scope='module', autouse=True)
def rumble_fixture(request):
    service = RumbleService()
    initialize_fixture(request, service)
    return service
