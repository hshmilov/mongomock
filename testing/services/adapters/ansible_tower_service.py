import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AnsibleTowerService(AdapterService):
    def __init__(self):
        super().__init__('ansible-tower')


@pytest.fixture(scope='module', autouse=True)
def ansible_tower_fixture(request):
    service = AnsibleTowerService()
    initialize_fixture(request, service)
    return service
