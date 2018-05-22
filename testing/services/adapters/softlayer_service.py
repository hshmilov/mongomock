import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SoftlayerService(AdapterService):
    def __init__(self):
        super().__init__('softlayer')


@pytest.fixture(scope="module", autouse=True)
def softlayer_fixture(request):
    service = SoftlayerService()
    initialize_fixture(request, service)
    return service
