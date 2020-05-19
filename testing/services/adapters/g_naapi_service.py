import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GNaapiService(AdapterService):
    def __init__(self):
        super().__init__('g-naapi')

    @property
    def volumes_override(self):
        volumes = super().volumes_override
        volumes.append(f'/home/ubuntu/cortex/adapters/aws_adapter:/home/axonius/app/aws_adapter:ro')
        return volumes


@pytest.fixture(scope='module', autouse=True)
def g_naapi_fixture(request):
    service = GNaapiService()
    initialize_fixture(request, service)
    return service
