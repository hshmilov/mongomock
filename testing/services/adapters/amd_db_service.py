import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AmdDbService(AdapterService):
    def __init__(self):
        super().__init__('amd-db')


@pytest.fixture(scope='module', autouse=True)
def amd_db_fixture(request):
    service = AmdDbService()
    initialize_fixture(request, service)
    return service
