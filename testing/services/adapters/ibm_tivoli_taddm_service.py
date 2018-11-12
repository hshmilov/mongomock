import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IbmTivoliTaddmService(AdapterService):
    def __init__(self):
        super().__init__('ibm-tivoli-taddm')


@pytest.fixture(scope='module', autouse=True)
def ibm_tivoli_taddm_fixture(request):
    service = IbmTivoliTaddmService()
    initialize_fixture(request, service)
    return service
