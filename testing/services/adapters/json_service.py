import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JsonService(AdapterService):
    def __init__(self):
        super().__init__('json')


@pytest.fixture(scope='module', autouse=True)
def json_fixture(request):
    service = JsonService()
    initialize_fixture(request, service)
    return service
