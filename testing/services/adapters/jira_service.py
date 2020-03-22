import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JiraService(AdapterService):
    def __init__(self):
        super().__init__('jira')


@pytest.fixture(scope='module', autouse=True)
def jira_fixture(request):
    service = JiraService()
    initialize_fixture(request, service)
    return service
