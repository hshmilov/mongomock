from services.plugin_service import PluginService


class StaticUsersCorrelatorService(PluginService):
    def __init__(self):
        super().__init__('static-users-correlator')
