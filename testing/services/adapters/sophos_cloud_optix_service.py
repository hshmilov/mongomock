import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SophosCloudOptixService(AdapterService):
    def __init__(self):
        super().__init__('sophos-cloud-optix')


@pytest.fixture(scope='module', autouse=True)
def sophos_cloud_optix_fixture(request):
    service = SophosCloudOptixService()
    initialize_fixture(request, service)
    return service
