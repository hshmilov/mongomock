import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NextThinkService(AdapterService):
    def __init__(self):
        super().__init__('next-think')


@pytest.fixture(scope='module', autouse=True)
def next_think_fixture(request):
    service = NextThinkService()
    initialize_fixture(request, service)
    return service
