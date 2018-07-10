import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GoogleMdmService(AdapterService):
    def __init__(self):
        super().__init__('google-mdm')


@pytest.fixture(scope="module", autouse=True)
def google_mdm_fixture(request):
    service = GoogleMdmService()
    initialize_fixture(request, service)
    return service
