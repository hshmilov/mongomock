import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ChefService(AdapterService):
    def __init__(self):
        super().__init__('chef')


@pytest.fixture(scope="module", autouse=True)
def chef_fixture(request):
    service = ChefService()
    initialize_fixture(request, service)
    return service
