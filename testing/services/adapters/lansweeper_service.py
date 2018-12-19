import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class LansweeperService(AdapterService):
    def __init__(self):
        super().__init__('lansweeper')


@pytest.fixture(scope='module', autouse=True)
def lansweeper_fixture(request):
    service = LansweeperService()
    initialize_fixture(request, service)
    return service
