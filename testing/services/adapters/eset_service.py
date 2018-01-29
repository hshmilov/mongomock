import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class EsetService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__('eset', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def eset_fixture(request):
    service = EsetService()
    initialize_fixture(request, service)
    return service
