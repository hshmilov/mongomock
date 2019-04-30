import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AlertlogicService(AdapterService):
    def __init__(self):
        super().__init__('alertlogic')


@pytest.fixture(scope='module', autouse=True)
def alertlogic_fixture(request):
    service = AlertlogicService()
    initialize_fixture(request, service)
    return service
