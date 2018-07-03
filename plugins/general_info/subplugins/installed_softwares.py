from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import wmi_query_commands, smb_shell_commands, is_wmi_answer_ok
from general_info.utils.nvd_nist.nvd_search import NVDSearcher
from axonius.devices.device_adapter import DeviceAdapter
from axonius.background_scheduler import LoggedBackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
import threading
from datetime import datetime, timedelta


GET_INSTALLED_SOFTWARE_COMMANDS = [
    r'reg query HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\ /reg:32 /s',
    r'reg query HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\ /reg:64 /s',
    r'reg query HKLM\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\ /reg:32 /s',
    r'reg query HKLM\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\ /reg:64 /s',
    'for /f %a in (\'reg query hku\') do (reg query "%a\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall" /reg:64 /s)',
    'for /f %a in (\'reg query hku\') do (reg query "%a\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall" /reg:32 /s)'
]


NVD_DB_UPDATE_HOURS = 12     # amount of hours after of which we update the db, if possible


class GetInstalledSoftwares(GeneralInfoSubplugin):
    """ Using wmi queries, determines all installed software on the machine. """
    nvd_objects_lock = threading.Lock()
    nvd_searcher = None
    nvd_updater_scheduler = None

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

        # If not initialized yet, initialize NVDSearcher
        try:
            with GetInstalledSoftwares.nvd_objects_lock:
                if GetInstalledSoftwares.nvd_searcher is None:
                    self.logger.info("Initializing NVDSearcher")
                    GetInstalledSoftwares.nvd_searcher = NVDSearcher()

                if GetInstalledSoftwares.nvd_updater_scheduler is None:
                    self.logger.info("Initializing background scheduler for updating nvd nist")
                    executors = {'default': ThreadPoolExecutor(1)}
                    GetInstalledSoftwares.nvd_updater_scheduler = LoggedBackgroundScheduler(executors=executors)

                    # Thread for resolving IP addresses of devices
                    GetInstalledSoftwares.nvd_updater_scheduler.add_job(
                        func=self._update_nvd_db,
                        trigger=IntervalTrigger(hours=NVD_DB_UPDATE_HOURS),
                        next_run_time=datetime.now() + timedelta(hours=NVD_DB_UPDATE_HOURS),
                        name='update_nvd_db_thread',
                        id='update_nvd_db_thread',
                        max_instances=1)

                    GetInstalledSoftwares.nvd_updater_scheduler.start()
        except Exception:
            self.logger.exception("An error occured while initializing NVDSearcher! Not using it")

    def _update_nvd_db(self):
        """
        Updates the NVD DB.
        :return:
        """
        try:
            self.logger.info("Trying to update the nvd db..")
            with GetInstalledSoftwares.nvd_objects_lock:
                if GetInstalledSoftwares.nvd_searcher is not None:
                    GetInstalledSoftwares.nvd_searcher.update()
                    self.logger.info("Successfully updated nvd db")
                else:
                    self.logger.error("NVDSearcher is not initialized! Not updating")
        except Exception:
            self.logger.exception("Failure while updating nvd_searcher, bypassing")

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands(["select Vendor, Name, Version, InstallState from Win32_Product"]) + \
            smb_shell_commands(GET_INSTALLED_SOFTWARE_COMMANDS)

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)

        installed_software = set()

        win32_product_answer = result[0]["data"]
        # we have a list of cmd commands, lets join to one big output.
        exec_installed_software = "\n".join([i["data"] for i in result[1:]])

        if is_wmi_answer_ok(result[0]):
            try:
                for i in win32_product_answer:
                    if i.get("InstallState") == 5:
                        # 5 means it's installed
                        installed_software.add((i['Vendor'], i['Name'], i['Version']))
            except Exception:
                self.logger.exception("Exception while handling win32_product")

        # Each software contains firstly the registry key, the following one appears in all of them.
        for software_details in exec_installed_software.split(r"Microsoft\Windows\CurrentVersion"):
            r"""
            Example of a software_details string. Note that not all vars can be there.

            HKEY_LOCAL_MACHINE\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{F8CFEB22-A2E7-3971-9EDA-4B11EDEFC185}
            AuthorizedCDFPrefix    REG_SZ
            Comments    REG_SZ    Caution. Removing this product might prevent some applications from running.
            Contact    REG_SZ
            DisplayVersion    REG_SZ    12.0.21005
            HelpLink    REG_EXPAND_SZ    http://go.microsoft.com/fwlink/?LinkId=133405
            HelpTelephone    REG_SZ
            InstallDate    REG_SZ    20170724
            InstallLocation    REG_SZ
            InstallSource    REG_SZ    C:\ProgramData\Package Cache\{F8CFEB22-A2E7-3971-9EDA-4B11EDEFC185}v12.0.21005\packages\vcRuntimeAdditional_x86\
            ModifyPath    REG_EXPAND_SZ    MsiExec.exe /X{F8CFEB22-A2E7-3971-9EDA-4B11EDEFC185}
            NoModify    REG_DWORD    0x1
            Publisher    REG_SZ    Microsoft Corporation
            Readme    REG_SZ
            Size    REG_SZ
            EstimatedSize    REG_DWORD    0x13e9
            SystemComponent    REG_DWORD    0x1
            UninstallString    REG_EXPAND_SZ    MsiExec.exe /X{F8CFEB22-A2E7-3971-9EDA-4B11EDEFC185}
            URLInfoAbout    REG_SZ
            URLUpdateInfo    REG_SZ
            VersionMajor    REG_DWORD    0xc
            VersionMinor    REG_DWORD    0x0
            WindowsInstaller    REG_DWORD    0x1
            Version    REG_DWORD    0xc00520d
            Language    REG_DWORD    0x409
            DisplayName    REG_SZ    Microsoft Visual C++ 2013 x86 Additional Runtime - 12.0.21005
            sEstimatedSize2    REG_DWORD    0x24f0
            """
            software = {}
            for line in software_details[1:].split("\n"):
                # Notice that the first line doesn't matter since we cut it
                # when we split(r"HKEY_LOCAL_MACHINE\Software")
                try:
                    line_name, _, line_value = line.strip().split("    ")
                    software[line_name] = line_value.strip()
                except Exception:
                    pass

            # Now that we have parsed it.. If we only have the name its enough. the rest is bonus.
            if software.get("DisplayName") is not None:
                installed_software.add(
                    (software.get("Publisher"), software.get("DisplayName"), software.get("DisplayVersion")))

        # Now finally add everything here.
        with GetInstalledSoftwares.nvd_objects_lock:
            for software_vendor, software_name, software_version in installed_software:
                # Add it to the installed softwares
                adapterdata_device.add_installed_software(
                    vendor=software_vendor,
                    name=software_name,
                    version=software_version
                )

                if GetInstalledSoftwares.nvd_searcher is None:
                    continue

                try:
                    # Search for CVE's!
                    if software_vendor is None or software_name is None or software_version is None:
                        # Sometimes, that happens.
                        continue
                    cves = GetInstalledSoftwares.nvd_searcher.search_vuln(
                        software_vendor, software_name, software_version)

                    for cve in cves:
                        try:
                            cve_id = cve["id"]
                            cve_description = cve.get("description")
                            cve_references = cve.get("references")
                            cve_severity = cve.get("severity")

                            adapterdata_device.add_vulnerable_software(
                                software_vendor=software_vendor,
                                software_name=software_name,
                                software_version=software_version,
                                cve_id=cve_id,
                                cve_description=cve_description,
                                cve_references=cve_references,
                                cve_severity=cve_severity
                            )
                        except Exception:
                            self.logger.exception(
                                f"Exception parsing cve {cve} for {software_vendor}:{software_name}:{software_version}")
                except Exception:
                    self.logger.exception(
                        f"Exception while searching for vuln for {software_vendor}:{software_name}:{software_version}")

        return True
