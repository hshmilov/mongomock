import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FireeyeHxService(AdapterService):
    def __init__(self):
        super().__init__('fireeye-hx')


@pytest.fixture(scope="module", autouse=True)
def fireeye_hx_fixture(request):
    service = FireeyeHxService()
    initialize_fixture(request, service)
    return service
