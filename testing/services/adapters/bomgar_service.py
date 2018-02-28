import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class BomgarService(AdapterService):
    def __init__(self):
        super().__init__('bomgar')


@pytest.fixture(scope="module", autouse=True)
def bomgar_fixture(request):
    service = BomgarService()
    initialize_fixture(request, service)
    return service
