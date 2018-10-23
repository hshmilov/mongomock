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
        CheckReg.__reg_check_exists = [key.get('key_name') for key in reg_check_exists.values() if key]

    @staticmethod
    def get_wmi_smb_commands():
        if CheckReg.__reg_check_exists:
            reg_list = [f'reg query "{reg_key}" /ve' for reg_key in CheckReg.__reg_check_exists]
        else:
            reg_list = []
        return smb_shell_commands(reg_list)

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)
        adapterdata_device.reg_key_exists = []
        adapterdata_device.reg_key_not_exists = []

        if not CheckReg.__reg_check_exists:
            return True
        got_ok = True
        for i, reg_key in enumerate(CheckReg.__reg_check_exists):
            if not is_wmi_answer_ok(result[i]):
                self.logger.error(f'wmi answer for reg key {reg_key} error: {result[i]}')
                got_ok = False
                continue
            try:
                result_reg = result[i]['data']
                if '(default)' in result_reg.lower():
                    adapterdata_device.reg_key_exists.append(reg_key)
                else:
                    adapterdata_device.reg_key_not_exists.append(reg_key)
            except Exception:
                self.logger.exception(f'Problem getting reg key exists or not ')

        return got_ok
