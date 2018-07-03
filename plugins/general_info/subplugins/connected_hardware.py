from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import wmi_query_commands, smb_shell_commands, is_wmi_answer_ok
from axonius.devices.device_adapter import DeviceAdapter


class GetConnectedHardware(GeneralInfoSubplugin):
    """ Using wmi queries, determines all Plug and play devices (hardware) connected """

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands(["select DeviceID, Name, Manufacturer, PNPClass from Win32_PnPEntity"])

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)

        connected_hardware_answer = result[0]["data"]
        if is_wmi_answer_ok(result[0]):
            try:
                for connected_hw_raw in connected_hardware_answer:
                    adapterdata_device.add_connected_hardware(hw_id=connected_hw_raw.get("DeviceID"),
                                                              name=connected_hw_raw.get("Name"),
                                                              manufacturer=connected_hw_raw.get("Manufacturer"),
                                                              pnp_class=connected_hw_raw.get("PNPClass"))
            except Exception:
                self.logger.exception(f"Wmi answer for usb device exception: {result}")
        return True
