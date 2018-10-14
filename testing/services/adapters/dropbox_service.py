import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class DropboxService(AdapterService):
    def __init__(self):
        super().__init__('dropbox')


@pytest.fixture(scope='module', autouse=True)
def dropbox_fixture(request):
    service = DropboxService()
    initialize_fixture(request, service)
    return service
