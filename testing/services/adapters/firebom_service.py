import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FirebomService(AdapterService):
    def __init__(self):
        super().__init__('firebom')


@pytest.fixture(scope='module', autouse=True)
def firebom_fixture(request):
    service = FirebomService()
    initialize_fixture(request, service)
    return service
