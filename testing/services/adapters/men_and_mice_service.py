import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MenAndMiceService(AdapterService):
    def __init__(self):
        super().__init__('men-and-mice')


@pytest.fixture(scope='module', autouse=True)
def men_and_mice_fixture(request):
    service = MenAndMiceService()
    initialize_fixture(request, service)
    return service
