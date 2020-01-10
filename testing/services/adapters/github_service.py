import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GithubService(AdapterService):
    def __init__(self):
        super().__init__('github')


@pytest.fixture(scope='module', autouse=True)
def github_fixture(request):
    service = GithubService()
    initialize_fixture(request, service)
    return service
