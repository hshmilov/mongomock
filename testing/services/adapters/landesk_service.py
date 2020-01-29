import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LandeskService(AdapterService):
    def __init__(self):
        super().__init__('landesk')


@pytest.fixture(scope='module', autouse=True)
def landesk_fixture(request):
    service = LandeskService()
    initialize_fixture(request, service)
    return service
