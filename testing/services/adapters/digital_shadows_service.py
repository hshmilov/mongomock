import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DigitalShadowsService(AdapterService):
    def __init__(self):
        super().__init__('digital-shadows')


@pytest.fixture(scope='module', autouse=True)
def digital_shadows_fixture(request):
    service = DigitalShadowsService()
    initialize_fixture(request, service)
    return service
