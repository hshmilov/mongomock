import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OneloginService(AdapterService):
    def __init__(self):
        super().__init__('onelogin')


@pytest.fixture(scope='module', autouse=True)
def onelogin_fixture(request):
    service = OneloginService()
    initialize_fixture(request, service)
    return service
