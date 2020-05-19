import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PureStorageFlashArrayService(AdapterService):
    def __init__(self):
        super().__init__('pure-storage-flash-array')


@pytest.fixture(scope='module', autouse=True)
def pure_storage_flash_array_fixture(request):
    service = PureStorageFlashArrayService()
    initialize_fixture(request, service)
    return service
