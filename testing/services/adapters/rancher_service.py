import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RancherService(AdapterService):
    def __init__(self):
        super().__init__('rancher')


@pytest.fixture(scope='module', autouse=True)
def rancher_fixture(request):
    service = RancherService()
    initialize_fixture(request, service)
    return service
