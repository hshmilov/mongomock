import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AdService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('ad', **kwargs)

    def resolve_ip(self):
        self.post('resolve_ip', None, None)


@pytest.fixture(scope="module", autouse=True)
def ad_fixture(request):
    service = AdService()
    initialize_fixture(request, service)
    return service
