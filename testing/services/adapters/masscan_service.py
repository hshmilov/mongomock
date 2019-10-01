import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MasscanService(AdapterService):
    def __init__(self):
        super().__init__('masscan')


@pytest.fixture(scope='module', autouse=True)
def masscan_fixture(request):
    service = MasscanService()
    initialize_fixture(request, service)
    return service
