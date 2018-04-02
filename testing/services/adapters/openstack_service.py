import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OpenstackService(AdapterService):
    def __init__(self):
        super().__init__('openstack')


@pytest.fixture(scope="module", autouse=True)
def openstack_fixture(request):
    service = OpenstackService()
    initialize_fixture(request, service)
    return service
