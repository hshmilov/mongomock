import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class ServiceNowSqlService(AdapterService):
    def __init__(self):
        super().__init__('service-now-sql')


@pytest.fixture(scope='module', autouse=True)
def service_now_sql_fixture(request):
    service = ServiceNowSqlService()
    initialize_fixture(request, service)
    return service
