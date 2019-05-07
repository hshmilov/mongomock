import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ZscalerService(AdapterService):
    def __init__(self):
        super().__init__('zscaler')


@pytest.fixture(scope='module', autouse=True)
def zscaler_fixture(request):
    service = ZscalerService()
    initialize_fixture(request, service)
    return service
