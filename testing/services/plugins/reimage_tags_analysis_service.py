import pytest
from services.plugin_service import PluginService
from services.simple_fixture import initialize_fixture


class ReimageTagsAnalysisService(PluginService):
    def __init__(self):
        super().__init__('reimage-tags-analysis')


@pytest.fixture(scope='module')
def reimage_tags_analysis_fixture(request):
    service = ReimageTagsAnalysisService()
    initialize_fixture(request, service)
    return service
