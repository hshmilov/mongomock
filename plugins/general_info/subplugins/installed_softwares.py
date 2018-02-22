from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from axonius.devices.device import Device


class GetInstalledSoftwares(GeneralInfoSubplugin):
    """ Using wmi queries, determines all installed software on the machine. """

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

    def handle_result(self, device, executer_info, result, adapterdata_device: Device):

        installed_softwares = []
        for i in result[0]:
            if i["InstallState"] == 5:
                # 5 means it's installed
                installed_softwares.append(
                    {
                        "Vendor": i['Vendor'],
                        "Name": i['Name'],
                        "Version": i['Version']
                    }
                )

                adapterdata_device.add_installed_software(
                    vendor=i['Vendor'],
                    name=i['Name'],
                    version=i['Version']
                )
