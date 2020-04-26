import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PanoraysService(AdapterService):
    def __init__(self):
        super().__init__('panorays')


@pytest.fixture(scope='module', autouse=True)
def panorays_fixture(request):
    service = PanoraysService()
    initialize_fixture(request, service)
    return service
