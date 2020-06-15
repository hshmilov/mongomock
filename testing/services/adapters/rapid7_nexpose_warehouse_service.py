import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Rapid7NexposeWarehouseService(AdapterService):
    def __init__(self):
        super().__init__('rapid7-nexpose-warehouse')


@pytest.fixture(scope='module', autouse=True)
def rapid7_nexpose_warehouse_fixture(request):
    service = Rapid7NexposeWarehouseService()
    initialize_fixture(request, service)
    return service
