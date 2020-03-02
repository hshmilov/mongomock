import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OpenvasService(AdapterService):
    def __init__(self):
        super().__init__('openvas')


@pytest.fixture(scope='module', autouse=True)
def openvas_fixture(request):
    service = OpenvasService()
    initialize_fixture(request, service)
    return service
