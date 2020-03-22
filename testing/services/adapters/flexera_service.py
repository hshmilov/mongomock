import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FlexeraService(AdapterService):
    def __init__(self):
        super().__init__('flexera')


@pytest.fixture(scope='module', autouse=True)
def flexera_fixture(request):
    service = FlexeraService()
    initialize_fixture(request, service)
    return service
