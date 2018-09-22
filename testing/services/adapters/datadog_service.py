import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DatadogService(AdapterService):
    def __init__(self):
        super().__init__('datadog')


@pytest.fixture(scope='module', autouse=True)
def datadog_fixture(request):
    service = DatadogService()
    initialize_fixture(request, service)
    return service
