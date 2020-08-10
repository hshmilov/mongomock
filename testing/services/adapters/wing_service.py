import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WingService(AdapterService):
    def __init__(self):
        super().__init__('wing')


@pytest.fixture(scope='module', autouse=True)
def wing_fixture(request):
    service = WingService()
    initialize_fixture(request, service)
    return service
