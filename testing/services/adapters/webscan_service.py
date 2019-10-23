import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WebscanService(AdapterService):
    def __init__(self):
        super().__init__('webscan')


@pytest.fixture(scope='module', autouse=True)
def webscan_fixture(request):
    service = WebscanService()
    initialize_fixture(request, service)
    return service
