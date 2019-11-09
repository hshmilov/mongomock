import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PreemptService(AdapterService):
    def __init__(self):
        super().__init__('preempt')


@pytest.fixture(scope='module', autouse=True)
def preempt_fixture(request):
    service = PreemptService()
    initialize_fixture(request, service)
    return service
