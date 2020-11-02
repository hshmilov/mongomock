import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BitbucketService(AdapterService):
    def __init__(self):
        super().__init__('bitbucket')


@pytest.fixture(scope='module', autouse=True)
def bitbucket_fixture(request):
    service = BitbucketService()
    initialize_fixture(request, service)
    return service
