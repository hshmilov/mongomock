import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MobileironService(AdapterService):
    def __init__(self):
        super().__init__('mobileiron')


@pytest.fixture(scope="module", autouse=True)
def mobileiron_fixture(request):
    service = MobileironService()
    initialize_fixture(request, service)
    return service
