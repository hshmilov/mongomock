import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class TaniumAssetService(AdapterService):
    def __init__(self):
        super().__init__('tanium-asset')


@pytest.fixture(scope='module', autouse=True)
def tanium_asset_fixture(request):
    service = TaniumAssetService()
    initialize_fixture(request, service)
    return service
