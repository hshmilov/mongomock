import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecSepCloudService(AdapterService):
    def __init__(self):
        super().__init__('symantec-sep-cloud')


@pytest.fixture(scope='module', autouse=True)
def symantec_sep_cloud_fixture(request):
    service = SymantecSepCloudService()
    initialize_fixture(request, service)
    return service
