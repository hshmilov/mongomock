import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SplunkService(AdapterService):
    def __init__(self):
        super().__init__('splunk')


@pytest.fixture(scope='module', autouse=True)
def splunk_fixture(request):
    service = SplunkService()
    initialize_fixture(request, service)
    return service
