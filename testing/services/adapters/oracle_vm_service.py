import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class OracleVmService(AdapterService):
    def __init__(self):
        super().__init__('oracle-vm')


@pytest.fixture(scope="module", autouse=True)
def oracle_vm_fixture(request):
    service = OracleVmService()
    initialize_fixture(request, service)
    return service
