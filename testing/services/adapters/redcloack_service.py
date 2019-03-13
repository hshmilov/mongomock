import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RedcloackService(AdapterService):
    def __init__(self):
        super().__init__('redcloack')


@pytest.fixture(scope='module', autouse=True)
def redcloack_fixture(request):
    service = RedcloackService()
    initialize_fixture(request, service)
    return service
