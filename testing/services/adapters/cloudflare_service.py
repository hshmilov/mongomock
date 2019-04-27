import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CloudflareService(AdapterService):
    def __init__(self):
        super().__init__('cloudflare')


@pytest.fixture(scope='module', autouse=True)
def cloudflare_fixture(request):
    service = CloudflareService()
    initialize_fixture(request, service)
    return service
