"""
Using wmi queries, determines basic computer info
"""
from .general_info_subplugin import GeneralInfoSubplugin


class GetBasicComputerInfo(GeneralInfoSubplugin):
    """
    Gets all basic computer info on that machine.
    """

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        super().__init__(plugin_base_delegate)
        self.users = {}  # a cache var for storing users from adapters.
        self.logger.info("Initialized BasicComputerInfo plugin")

    def get_wmi_commands(self):
        return [
            {"type": "query", "args": ["select * from Win32_Processor"]},
            {"type": "query", "args": ["select * from Win32_BIOS"]},
            {"type": "query", "args": ["select * from Win32_ComputerSystemProduct"]},
            {"type": "query", "args": ["select * from Win32_DiskDrive"]},
            {"type": "query", "args": ["select * from Win32_QuickFixEngineering"]},
            {"type": "query", "args": ["select * from Win32_OperatingSystem"]}
        ]

    def handle_result(self, device, executer_info, result):
        pass
