import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BigfixService(AdapterService):
    def __init__(self):
        super().__init__('bigfix')


@pytest.fixture(scope="module", autouse=True)
def bigfix_fixture(request):
    service = BigfixService()
    initialize_fixture(request, service)
    return service
