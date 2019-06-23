import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CycognitoService(AdapterService):
    def __init__(self):
        super().__init__('cycognito')


@pytest.fixture(scope='module', autouse=True)
def cycognito_fixture(request):
    service = CycognitoService()
    initialize_fixture(request, service)
    return service
