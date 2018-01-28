import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PuppetService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('puppet', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def puppet_fixture(request):
    service = PuppetService()
    initialize_fixture(request, service)
    return service
