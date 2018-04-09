import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CarbonblackService(AdapterService):
    def __init__(self):
        super().__init__('carbonblack')


@pytest.fixture(scope="module", autouse=True)
def carbonblack_fixture(request):
    service = CarbonblackService()
    initialize_fixture(request, service)
    return service
