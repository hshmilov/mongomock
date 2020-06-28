import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SonicWallService(AdapterService):
    def __init__(self):
        super().__init__('sonic-wall')


@pytest.fixture(scope='module', autouse=True)
def sonic_wall_fixture(request):
    service = SonicWallService()
    initialize_fixture(request, service)
    return service
