import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class QuestKaceService(AdapterService):
    def __init__(self):
        super().__init__('quest-kace')


@pytest.fixture(scope='module', autouse=True)
def quest_kace_fixture(request):
    service = QuestKaceService()
    initialize_fixture(request, service)
    return service
