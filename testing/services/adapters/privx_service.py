import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PrivxService(AdapterService):
    def __init__(self):
        super().__init__('privx')


@pytest.fixture(scope='module', autouse=True)
def privx_fixture(request):
    service = PrivxService()
    initialize_fixture(request, service)
    return service
