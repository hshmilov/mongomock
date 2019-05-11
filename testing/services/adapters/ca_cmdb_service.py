import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CaCmdbService(AdapterService):
    def __init__(self):
        super().__init__('ca-cmdb')


@pytest.fixture(scope='module', autouse=True)
def ca_cmdb_fixture(request):
    service = CaCmdbService()
    initialize_fixture(request, service)
    return service
