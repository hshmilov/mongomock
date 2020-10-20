import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BmcAtriumService(AdapterService):
    def __init__(self):
        super().__init__('bmc-atrium')


@pytest.fixture(scope='module', autouse=True)
def bmc_atrium_fixture(request):
    service = BmcAtriumService()
    initialize_fixture(request, service)
    return service
