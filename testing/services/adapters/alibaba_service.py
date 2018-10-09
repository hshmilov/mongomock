import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AlibabaService(AdapterService):
    def __init__(self):
        super().__init__('alibaba')


@pytest.fixture(scope='module', autouse=True)
def alibaba_fixture(request):
    service = AlibabaService()
    initialize_fixture(request, service)
    return service
