import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ClearpassService(AdapterService):
    def __init__(self):
        super().__init__('clearpass')


@pytest.fixture(scope='module', autouse=True)
def clearpass_fixture(request):
    service = ClearpassService()
    initialize_fixture(request, service)
    return service
