import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class VmwareVropsService(AdapterService):
    def __init__(self):
        super().__init__('vmware-vrops')


@pytest.fixture(scope='module', autouse=True)
def vmware_vrops_fixture(request):
    service = VmwareVropsService()
    initialize_fixture(request, service)
    return service
