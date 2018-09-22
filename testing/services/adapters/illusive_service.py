import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IllusiveService(AdapterService):
    def __init__(self):
        super().__init__('illusive')


@pytest.fixture(scope='module', autouse=True)
def illusive_fixture(request):
    service = IllusiveService()
    initialize_fixture(request, service)
    return service
