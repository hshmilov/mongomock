import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class RedcanaryService(AdapterService):
    def __init__(self):
        super().__init__('redcanary')


@pytest.fixture(scope='module', autouse=True)
def redcanary_fixture(request):
    service = RedcanaryService()
    initialize_fixture(request, service)
    return service
