import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class AwsService(AdapterService):
    def __init__(self, **kwargs):
        super().__init__(service_dir='../adapters/aws-adapter', **kwargs)


@pytest.fixture(scope="module", autouse=True)
def aws_fixture(request):
    service = AwsService()
    initialize_fixture(request, service)
    return service
