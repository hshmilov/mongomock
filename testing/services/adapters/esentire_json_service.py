import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EsentireJsonService(AdapterService):
    def __init__(self):
        super().__init__('esentire-json')


@pytest.fixture(scope='module', autouse=True)
def esentire_json_fixture(request):
    service = EsentireJsonService()
    initialize_fixture(request, service)
    return service
