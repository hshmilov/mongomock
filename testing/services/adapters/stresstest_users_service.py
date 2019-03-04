import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class StresstestUsersService(AdapterService):
    def __init__(self):
        super().__init__('stresstest-users')


@pytest.fixture(scope='module', autouse=True)
def stresstestusers_fixture(request):
    service = StresstestUsersService()
    initialize_fixture(request, service)
    return service
