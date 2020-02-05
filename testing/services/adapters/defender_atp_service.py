import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DefenderAtpService(AdapterService):
    def __init__(self):
        super().__init__('defender-atp')


@pytest.fixture(scope='module', autouse=True)
def defender_atp_fixture(request):
    service = DefenderAtpService()
    initialize_fixture(request, service)
    return service
