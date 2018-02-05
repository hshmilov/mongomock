"""
Using wmi queries, determines all installed software on the machine.
"""
from .general_info_subplugin import GeneralInfoSubplugin


class GetInstalledSoftwares(GeneralInfoSubplugin):
    """
    Gets all installed softwares on that machine.
    """

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        super().__init__(plugin_base_delegate)
        self.users = {}  # a cache var for storing users from adapters.
        self.logger.info("Initialized InstalledSoftwares plugin")

    def get_wmi_commands(self):
        return [{"type": "query", "args": ["select Vendor, Name, Version, InstallState from Win32_Product"]}]

    def handle_result(self, device, executer_info, result):
        pass
