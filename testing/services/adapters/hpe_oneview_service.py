import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class HpeOneviewService(AdapterService):
    def __init__(self):
        super().__init__('hpe-oneview')


@pytest.fixture(scope='module', autouse=True)
def hpe_oneview_fixture(request):
    service = HpeOneviewService()
    initialize_fixture(request, service)
    return service
