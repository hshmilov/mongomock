import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SpiceworksService(AdapterService):
    def __init__(self):
        super().__init__('spiceworks')


@pytest.fixture(scope='module', autouse=True)
def spiceworks_fixture(request):
    service = SpiceworksService()
    initialize_fixture(request, service)
    return service
