import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SophosService(AdapterService):
    def __init__(self):
        super().__init__('sophos')

    def action(self, action_type):
        raise NotImplementedError()


@pytest.fixture(scope='module', autouse=True)
def sophos_fixture(request):
    service = SophosService()
    initialize_fixture(request, service)
    return service
