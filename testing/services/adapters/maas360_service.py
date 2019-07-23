import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class Maas360Service(AdapterService):
    def __init__(self):
        super().__init__('maas360')


@pytest.fixture(scope='module', autouse=True)
def maas360_fixture(request):
    service = Maas360Service()
    initialize_fixture(request, service)
    return service
