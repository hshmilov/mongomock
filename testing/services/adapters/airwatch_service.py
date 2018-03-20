import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AirwatchService(AdapterService):
    def __init__(self):
        super().__init__('airwatch')


@pytest.fixture(scope="module", autouse=True)
def airwatch_fixture(request):
    service = AirwatchService()
    initialize_fixture(request, service)
    return service
