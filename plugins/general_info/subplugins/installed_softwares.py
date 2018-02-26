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

    def handle_result(self, device, executer_info, result, adapterdata_device: Device, extra):
        super().handle_result(device, executer_info, result, adapterdata_device, extra)

        installed_software = set()

        # First, handle wmi.
        if not all(is_wmi_answer_ok(a) for a in result):
            self.logger.error("Not handling wmi installed softwares, moving on to exec installed softwares")

        else:
            for i in result[0]:
                if i.get("InstallState") == 5:
                    # 5 means it's installed
                    installed_software.add((i['Vendor'], i['Name'], i['Version']))

        # Now, handle psexec

        if extra.get("result") != "Success":
            self.logger.error(f"Installed Softwares execution error: {extra}")
            return False

        # we have a list of cmd commands, lets join to one big output.
        exec_installed_software = "\n".join(extra['product'])
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
        for software_vendor, software_name, software_version in installed_software:
            adapterdata_device.add_installed_software(
                vendor=software_vendor,
                name=software_name,
                version=software_version
            )

        return True
