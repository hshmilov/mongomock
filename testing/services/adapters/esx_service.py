import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EsxService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('esx', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def esx_fixture(request):
    service = EsxService()
    initialize_fixture(request, service)
    return service
