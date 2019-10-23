import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class IgarService(AdapterService):
    def __init__(self):
        super().__init__('igar')


@pytest.fixture(scope='module', autouse=True)
def igar_fixture(request):
    service = IgarService()
    initialize_fixture(request, service)
    return service
