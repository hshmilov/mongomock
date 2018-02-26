from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import wmi_query_commands, is_wmi_answer_ok
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

    @staticmethod
    def get_wmi_commands():
        return wmi_query_commands(["select Vendor, Name, Version, InstallState from Win32_Product"])

    def handle_result(self, device, executer_info, result, adapterdata_device: Device):
        super().handle_result(device, executer_info, result, adapterdata_device)
        if not all(is_wmi_answer_ok(a) for a in result):
            self.logger.info("Not handling result, result has exception")
            return False

        installed_software = []
        for i in result[0]:
            if i.get("InstallState") == 5:
                # 5 means it's installed
                installed_software.append(
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

        return True
