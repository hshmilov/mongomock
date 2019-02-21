import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TwistlockService(AdapterService):
    def __init__(self):
        super().__init__('twistlock')


@pytest.fixture(scope='module', autouse=True)
def twistlock_fixture(request):
    service = TwistlockService()
    initialize_fixture(request, service)
    return service
