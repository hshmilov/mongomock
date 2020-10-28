import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class FlexnetService(AdapterService):
    def __init__(self):
        super().__init__('flexnet')


@pytest.fixture(scope='module', autouse=True)
def flexnet_fixture(request):
    service = FlexnetService()
    initialize_fixture(request, service)
    return service
