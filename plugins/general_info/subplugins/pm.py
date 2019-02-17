from datetime import datetime

from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import is_wmi_answer_ok
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.datetime import parse_date


# DCOM Errors
DCOM_ERROR_PROBABLY_RPC_ACCESS_DENIED = "0x800706ba"
DCOM_ERROR_INTERNET_PROBLEMS = "0x80072EE2"


class GetAvailableSecurityPatches(GeneralInfoSubplugin):
    """ Using axr, for online computers, determines security patches which are not installed"""

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_wmi_smb_commands():
        return [{"type": "pmonline", "args": []}]

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)

        available_security_patches = result[0]["data"]
        if is_wmi_answer_ok(result[0]):
            try:
                for patch in result[0]['data']:
                    try:
                        pm_publish_date = patch.get("LastDeploymentChangeTime")
                        if pm_publish_date is not None:
                            try:
                                pm_publish_date = datetime.fromtimestamp(pm_publish_date)
                            except Exception:
                                pm_publish_date = parse_date(pm_publish_date)
                    except Exception:
                        self.logger.exception(f"Error parsing publish date of patch {patch}")
                        pass

                    pm_title = patch.get("Title")
                    pm_msrc_severity = patch.get("MsrcSeverity")
                    pm_type = patch.get("Type")
                    if pm_type != "Software" and pm_type != "Driver":
                        self.logger.error(f"Expected pm type to be Software/Driver but its {pm_type}")
                        pm_type = None

                    pm_categories = patch.get("Categories")
                    pm_security_bulletin_ids = patch.get("SecurityBulletinIDs")
                    pm_kb_article_ids = patch.get("KBArticleIDs")

                    # Validate Its all strings
                    if pm_categories is not None:
                        pm_categories = [str(x) for x in pm_categories]

                    if pm_security_bulletin_ids is not None:
                        pm_security_bulletin_ids = [str(x) for x in pm_security_bulletin_ids]

                    if pm_kb_article_ids is not None:
                        pm_kb_article_ids = [str(x) for x in pm_kb_article_ids]

                    adapterdata_device.add_available_security_patch(
                        title=pm_title,
                        security_bulletin_ids=pm_security_bulletin_ids,
                        kb_article_ids=pm_kb_article_ids,
                        msrc_severity=pm_msrc_severity,
                        patch_type=pm_type,
                        categories=pm_categories,
                        publish_date=pm_publish_date
                    )

                return True
            except Exception:
                self.logger.exception(f"Wmi answer for patch management exception: {result}")
        else:
            if result[0]['status'] != 'ok':
                if DCOM_ERROR_INTERNET_PROBLEMS in result[0]['data']:
                    # This can happen on computers with no internet or with internet problems
                    self.logger.warning("Error code 0x80072EE2. This happens when there is an internet access error.")
                    return True

            self.logger.exception(f"Couldn't get available security patches: {available_security_patches}")

        return False
