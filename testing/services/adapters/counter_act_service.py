import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CounterActService(AdapterService):
    def __init__(self):
        super().__init__('counter-act')


@pytest.fixture(scope='module', autouse=True)
def counter_act_fixture(request):
    service = CounterActService()
    initialize_fixture(request, service)
    return service
