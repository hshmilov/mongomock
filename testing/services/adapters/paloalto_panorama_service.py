import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PaloaltoPanoramaService(AdapterService):
    def __init__(self):
        super().__init__('paloalto-panorama')


@pytest.fixture(scope='module', autouse=True)
def paloalto_panorama_fixture(request):
    service = PaloaltoPanoramaService()
    initialize_fixture(request, service)
    return service
