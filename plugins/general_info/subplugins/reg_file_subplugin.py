from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import smb_shell_commands, is_wmi_answer_ok
from axonius.devices.device_adapter import DeviceAdapter


class CheckReg(GeneralInfoSubplugin):
    """ Using wmi queries, determines all Plug and play devices (hardware) connected """

    __reg_check_exists = {}

    def __init__(self, *args, reg_check_exists, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)
        CheckReg.__reg_check_exists = reg_check_exists

    @staticmethod
    def get_wmi_smb_commands():
        reg_list = [f'reg query "{CheckReg.__reg_check_exists}" /ve'] if CheckReg.__reg_check_exists else []
        return smb_shell_commands(reg_list)

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)
        if not CheckReg.__reg_check_exists:
            return True

        if not is_wmi_answer_ok(result[0]):
            return False
        try:
            result_reg = result[0]['data']
            if result_reg.startswith('ERROR:'):
                adapterdata_device.reg_check_exists = False
            else:
                adapterdata_device.reg_check_exists = True
        except Exception:
            self.logger.exception(f'Problem getting reg key exists or not ')

        return True
