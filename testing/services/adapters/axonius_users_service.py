import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AxoniusUsersService(AdapterService):
    def __init__(self):
        super().__init__('axonius-users')


@pytest.fixture(scope='module', autouse=True)
def axonius_users_fixture(request):
    service = AxoniusUsersService()
    initialize_fixture(request, service)
    return service
