import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SentinelOneService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('sentinelone', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def sentinelone_fixture(request):
    service = SentinelOneService()
    initialize_fixture(request, service)
    return service
