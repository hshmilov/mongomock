import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SignalsciencesService(AdapterService):
    def __init__(self):
        super().__init__('signalsciences')


@pytest.fixture(scope='module', autouse=True)
def signalsciences_fixture(request):
    service = SignalsciencesService()
    initialize_fixture(request, service)
    return service
