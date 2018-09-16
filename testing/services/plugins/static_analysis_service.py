from services.plugin_service import PluginService


class StaticAnalysisService(PluginService):
    def __init__(self):
        super().__init__('static-analysis')
