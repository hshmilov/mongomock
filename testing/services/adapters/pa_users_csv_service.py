import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class PaUsersCsvService(AdapterService):
    def __init__(self):
        super().__init__('pa-users-csv')


@pytest.fixture(scope='module', autouse=True)
def pa_users_csv_fixture(request):
    service = PaUsersCsvService()
    initialize_fixture(request, service)
    return service
