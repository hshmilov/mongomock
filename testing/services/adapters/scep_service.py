import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ScepService(AdapterService):
    def __init__(self):
        super().__init__('scep')


@pytest.fixture(scope='module', autouse=True)
def scep_fixture(request):
    service = ScepService()
    initialize_fixture(request, service)
    return service
