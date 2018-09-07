import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CrowdStrikeService(AdapterService):
    def __init__(self):
        super().__init__('crowd-strike')


@pytest.fixture(scope='module', autouse=True)
def crowd_strike_fixture(request):
    service = CrowdStrikeService()
    initialize_fixture(request, service)
    return service
