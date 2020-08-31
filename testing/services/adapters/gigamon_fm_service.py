import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GigamonFmService(AdapterService):
    def __init__(self):
        super().__init__('gigamon-fm')


@pytest.fixture(scope='module', autouse=True)
def gigamon_fm_fixture(request):
    service = GigamonFmService()
    initialize_fixture(request, service)
    return service
