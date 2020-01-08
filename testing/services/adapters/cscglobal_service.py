import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class CscglobalService(AdapterService):
    def __init__(self):
        super().__init__('cscglobal')


@pytest.fixture(scope='module', autouse=True)
def cscglobal_fixture(request):
    service = CscglobalService()
    initialize_fixture(request, service)
    return service
