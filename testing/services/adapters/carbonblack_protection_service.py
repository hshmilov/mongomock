import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CarbonblackProtectionService(AdapterService):
    def __init__(self):
        super().__init__('carbonblack-protection')


@pytest.fixture(scope="module", autouse=True)
def carbonblack_protection_fixture(request):
    service = CarbonblackProtectionService()
    initialize_fixture(request, service)
    return service
