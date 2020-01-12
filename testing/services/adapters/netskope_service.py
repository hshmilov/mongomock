import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NetskopeService(AdapterService):
    def __init__(self):
        super().__init__('netskope')


@pytest.fixture(scope='module', autouse=True)
def netskope_fixture(request):
    service = NetskopeService()
    initialize_fixture(request, service)
    return service
