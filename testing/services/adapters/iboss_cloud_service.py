import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IbossCloudService(AdapterService):
    def __init__(self):
        super().__init__('iboss-cloud')


@pytest.fixture(scope='module', autouse=True)
def iboss_cloud_fixture(request):
    service = IbossCloudService()
    initialize_fixture(request, service)
    return service
