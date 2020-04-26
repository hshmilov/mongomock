import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BigidService(AdapterService):
    def __init__(self):
        super().__init__('bigid')


@pytest.fixture(scope='module', autouse=True)
def bigid_fixture(request):
    service = BigidService()
    initialize_fixture(request, service)
    return service
