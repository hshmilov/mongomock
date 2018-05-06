import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CarbonblackResponseService(AdapterService):
    def __init__(self):
        super().__init__('carbonblack-response')


@pytest.fixture(scope="module", autouse=True)
def carbonblack_response_fixture(request):
    service = CarbonblackResponseService()
    initialize_fixture(request, service)
    return service
