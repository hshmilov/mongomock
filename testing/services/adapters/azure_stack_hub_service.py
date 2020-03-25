import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AzureStackHubService(AdapterService):
    def __init__(self):
        super().__init__('azure-stack-hub')


@pytest.fixture(scope='module', autouse=True)
def azure_stack_hub_fixture(request):
    service = AzureStackHubService()
    initialize_fixture(request, service)
    return service
