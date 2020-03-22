import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AvamarService(AdapterService):
    def __init__(self):
        super().__init__('avamar')


@pytest.fixture(scope='module', autouse=True)
def avamar_fixture(request):
    service = AvamarService()
    initialize_fixture(request, service)
    return service
