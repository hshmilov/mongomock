import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AzureAdService(AdapterService):
    def __init__(self):
        super().__init__('azure-ad')


@pytest.fixture(scope='module', autouse=True)
def azure_ad_fixture(request):
    service = AzureAdService()
    initialize_fixture(request, service)
    return service
