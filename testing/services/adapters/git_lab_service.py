import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GitLabService(AdapterService):
    def __init__(self):
        super().__init__('git-lab')


@pytest.fixture(scope='module', autouse=True)
def git_lab_fixture(request):
    service = GitLabService()
    initialize_fixture(request, service)
    return service
