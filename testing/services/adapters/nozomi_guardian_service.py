import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class NozomiGuardianService(AdapterService):
    def __init__(self):
        super().__init__('nozomi-guardian')


@pytest.fixture(scope='module', autouse=True)
def nozomi_guardian_fixture(request):
    service = NozomiGuardianService()
    initialize_fixture(request, service)
    return service
