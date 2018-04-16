import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class JsonFileService(AdapterService):
    def __init__(self):
        super().__init__('json-file')


@pytest.fixture(scope="module", autouse=True)
def json_file_fixture(request):
    service = JsonFileService()
    initialize_fixture(request, service)
    return service
