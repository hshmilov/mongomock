import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CheckpointR80Service(AdapterService):
    def __init__(self):
        super().__init__('checkpoint-r80')


@pytest.fixture(scope='module', autouse=True)
def checkpoint_r80_fixture(request):
    service = CheckpointR80Service()
    initialize_fixture(request, service)
    return service
