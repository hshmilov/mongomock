from services.plugin_service import PluginService


class StaticCorrelatorService(PluginService):
    def __init__(self):
        super().__init__('static-correlator', service_dir='../plugins/static-correlator-plugin')
