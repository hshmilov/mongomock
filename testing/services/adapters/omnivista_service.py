import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OmnivistaService(AdapterService):
    def __init__(self):
        super().__init__('omnivista')


@pytest.fixture(scope='module', autouse=True)
def omnivista_fixture(request):
    service = OmnivistaService()
    initialize_fixture(request, service)
    return service
