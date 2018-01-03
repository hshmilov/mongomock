import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SplunkSymantecService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/splunk-symantec-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def splunk_symantec_fixture(request):
    service = SplunkSymantecService()
    initialize_fixture(request, service)
    return service
