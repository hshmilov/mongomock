import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PaloaltoXdrService(AdapterService):
    def __init__(self):
        super().__init__('paloalto-xdr')


@pytest.fixture(scope='module', autouse=True)
def paloalto_xdr_fixture(request):
    service = PaloaltoXdrService()
    initialize_fixture(request, service)
    return service
