from services.plugin_service import PluginService


class SystemSchedulerService(PluginService):
    def __init__(self):
        super().__init__('system-scheduler')
