import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EndgameService(AdapterService):
    def __init__(self):
        super().__init__('endgame')


@pytest.fixture(scope='module', autouse=True)
def endgame_fixture(request):
    service = EndgameService()
    initialize_fixture(request, service)
    return service
