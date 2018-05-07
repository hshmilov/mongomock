import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class InfiniteSleepService(AdapterService):
    def __init__(self):
        super().__init__('infinite-sleep')


@pytest.fixture(scope="module", autouse=True)
def infinite_sleep_fixture(request):
    service = InfiniteSleepService()
    initialize_fixture(request, service)
    return service
