import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CarbonblackDefenseService(AdapterService):
    def __init__(self):
        super().__init__('carbonblack-defense')


@pytest.fixture(scope="module", autouse=True)
def carbonblack_defense_fixture(request):
    service = CarbonblackDefenseService()
    initialize_fixture(request, service)
    return service
