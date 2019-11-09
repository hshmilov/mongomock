import pytest

from services.plugin_service import AdapterService
from services.simple_fixture import initialize_fixture


class GoogleBigQueryService(AdapterService):
    def __init__(self):
        super().__init__('google-big-query')


@pytest.fixture(scope='module', autouse=True)
def google_big_query_fixture(request):
    service = GoogleBigQueryService()
    initialize_fixture(request, service)
    return service
