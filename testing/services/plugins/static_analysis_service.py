import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class StaticAnalysisService(PluginService):
    def __init__(self):
        super().__init__('static-analysis')


@pytest.fixture(scope='module')
def static_analysis_fixture(request):
    service = StaticAnalysisService()
    initialize_fixture(request, service)
    return service
