import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RedsealService(AdapterService):
    def __init__(self):
        super().__init__('redseal')


@pytest.fixture(scope="module", autouse=True)
def redseal_fixture(request):
    service = RedsealService()
    initialize_fixture(request, service)
    return service
