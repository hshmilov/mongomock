import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BluecatService(AdapterService):
    def __init__(self):
        super().__init__('bluecat')


@pytest.fixture(scope='module', autouse=True)
def bluecat_fixture(request):
    service = BluecatService()
    initialize_fixture(request, service)
    return service
