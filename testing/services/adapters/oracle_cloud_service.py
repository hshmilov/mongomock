import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OracleCloudService(AdapterService):
    def __init__(self):
        super().__init__('oracle-cloud')


@pytest.fixture(scope='module', autouse=True)
def oracle_cloud_fixture(request):
    service = OracleCloudService()
    initialize_fixture(request, service)
    return service
