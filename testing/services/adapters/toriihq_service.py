import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ToriihqService(AdapterService):
    def __init__(self):
        super().__init__('toriihq')


@pytest.fixture(scope='module', autouse=True)
def toriihq_fixture(request):
    service = ToriihqService()
    initialize_fixture(request, service)
    return service
