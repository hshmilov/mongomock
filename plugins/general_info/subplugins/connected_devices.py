from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import wmi_query_commands, smb_shell_commands, is_wmi_answer_ok
from axonius.devices.device_adapter import DeviceAdapter


class GetConnectedDevices(GeneralInfoSubplugin):
    """ Using wmi queries, determines all usb devices on the machine. """

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands(["select DeviceID, Name, Manufacturer, PNPClass from Win32_PnPEntity "])

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)

        connected_devices_answer = result[0]["data"]
        if is_wmi_answer_ok(result[0]):
            try:
                for connected_device_raw in connected_devices_answer:
                    adapterdata_device.add_connected_device(device_id=connected_device_raw.get("DeviceID"),
                                                            name=connected_device_raw.get("Name"),
                                                            manufacturer=connected_device_raw.get("Manufacturer"),
                                                            pnp_class=connected_device_raw.get("PNPClass"))
            except Exception:
                self.logger.exception(f"Wmi answer for usb device exception: {result}")
        return True
