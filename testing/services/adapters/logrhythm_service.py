import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LogrhythmService(AdapterService):
    def __init__(self):
        super().__init__('logrhythm')


@pytest.fixture(scope='module', autouse=True)
def logrhythm_fixture(request):
    service = LogrhythmService()
    initialize_fixture(request, service)
    return service
