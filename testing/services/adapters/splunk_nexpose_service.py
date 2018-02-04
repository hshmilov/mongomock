import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SplunkNexposeService(AdapterService):
    def __init__(self):
        super().__init__('splunk-nexpose')


@pytest.fixture(scope="module", autouse=True)
def splunk_nexpose_fixture(request):
    service = SplunkNexposeService()
    initialize_fixture(request, service)
    return service
