from services.plugin_service import PluginService


class CarefulExecutionCorrelatorService(PluginService):
    def __init__(self):
        super().__init__('careful-execution-correlator', service_dir='../plugins/careful-execution-correlator-plugin')
