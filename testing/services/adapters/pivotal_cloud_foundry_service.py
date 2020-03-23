import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PivotalCloudFoundryService(AdapterService):
    def __init__(self):
        super().__init__('pivotal-cloud-foundry')


@pytest.fixture(scope='module', autouse=True)
def pivotal_cloud_foundry_fixture(request):
    service = PivotalCloudFoundryService()
    initialize_fixture(request, service)
    return service
