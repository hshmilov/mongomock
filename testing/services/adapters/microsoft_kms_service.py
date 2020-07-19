import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class MicrosoftKmsService(AdapterService):
    def __init__(self):
        super().__init__('microsoft-kms')


@pytest.fixture(scope='module', autouse=True)
def microsoft_kms_fixture(request):
    service = MicrosoftKmsService()
    initialize_fixture(request, service)
    return service
