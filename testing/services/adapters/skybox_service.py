import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SkyboxService(AdapterService):
    def __init__(self):
        super().__init__('skybox')


@pytest.fixture(scope='module', autouse=True)
def skybox_fixture(request):
    service = SkyboxService()
    initialize_fixture(request, service)
    return service
