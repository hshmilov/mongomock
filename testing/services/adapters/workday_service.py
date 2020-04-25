import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class WorkdayService(AdapterService):
    def __init__(self):
        super().__init__('workday')


@pytest.fixture(scope='module', autouse=True)
def workday_fixture(request):
    service = WorkdayService()
    initialize_fixture(request, service)
    return service
