import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class VcloudDirectorService(AdapterService):
    def __init__(self):
        super().__init__('vcloud-director')


@pytest.fixture(scope='module', autouse=True)
def vcloud_director_fixture(request):
    service = VcloudDirectorService()
    initialize_fixture(request, service)
    return service
