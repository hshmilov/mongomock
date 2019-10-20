import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BigfixInventoryService(AdapterService):
    def __init__(self):
        super().__init__('bigfix-inventory')


@pytest.fixture(scope='module', autouse=True)
def bigfix_inventory_fixture(request):
    service = BigfixInventoryService()
    initialize_fixture(request, service)
    return service
