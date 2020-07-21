import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class SlackService(AdapterService):
    def __init__(self):
        super().__init__('slack')


@pytest.fixture(scope='module', autouse=True)
def slack_fixture(request):
    service = SlackService()
    initialize_fixture(request, service)
    return service
