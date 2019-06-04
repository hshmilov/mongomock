import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CensysService(AdapterService):
    def __init__(self):
        super().__init__('censys')


@pytest.fixture(scope='module', autouse=True)
def censys_fixture(request):
    service = CensysService()
    initialize_fixture(request, service)
    return service
