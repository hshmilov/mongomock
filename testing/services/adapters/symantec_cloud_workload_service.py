import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SymantecCloudWorkloadService(AdapterService):
    def __init__(self):
        super().__init__('symantec-cloud-workload')


@pytest.fixture(scope='module', autouse=True)
def symantec_cloud_workload_fixture(request):
    service = SymantecCloudWorkloadService()
    initialize_fixture(request, service)
    return service
