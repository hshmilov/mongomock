import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GceService(AdapterService):
    def __init__(self):
        super().__init__('gce')


@pytest.fixture(scope="module", autouse=True)
def gce_fixture(request):
    service = GceService()
    initialize_fixture(request, service)
    return service
