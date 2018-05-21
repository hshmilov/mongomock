import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AzureService(AdapterService):
    def __init__(self):
        super().__init__('azure')


@pytest.fixture(scope="module", autouse=True)
def azure_fixture(request):
    service = AzureService()
    initialize_fixture(request, service)
    return service
