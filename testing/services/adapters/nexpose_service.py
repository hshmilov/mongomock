import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NexposeService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('nexpose', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def nexpose_fixture(request):
    service = NexposeService()
    initialize_fixture(request, service)
    return service
