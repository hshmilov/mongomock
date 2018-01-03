import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JamfService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/jamf-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def jamf_fixture(request):
    service = JamfService()
    initialize_fixture(request, service)
    return service
