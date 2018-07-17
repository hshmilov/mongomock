import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SolarwindsOrionService(AdapterService):
    def __init__(self):
        super().__init__('solarwinds-orion')


@pytest.fixture(scope="module", autouse=True)
def solarwinds_orion_fixture(request):
    service = SolarwindsOrionService()
    initialize_fixture(request, service)
    return service
