from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import parse_date
from axonius.utils import str2bool
from general_info.subplugins.general_info_subplugin import GeneralInfoSubplugin
from general_info.subplugins.wmi_utils import wmi_date_to_datetime, wmi_query_commands, \
    smb_shell_commands, is_wmi_answer_ok, reg_view_output_to_dict, reg_view_parse_int


BAD_CONFIGURATIONS_COMMANDS = [
    r'reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa\ '
]


class GetBasicComputerInfo(GeneralInfoSubplugin):
    """ Using wmi queries, determines basic computer info """

    def __init__(self, *args, **kwargs):
        """
        initialization.
        """
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_wmi_smb_commands():
        return wmi_query_commands([
            "select Name, AddressWidth, NumberOfCores, LoadPercentage, Architecture, "
            "MaxClockSpeed from Win32_Processor",

            "select SMBIOSBIOSVersion, SerialNumber from Win32_BIOS",
            "select Caption, Description, Version, BuildNumber, InstallDate, TotalVisibleMemorySize, "
            "FreePhysicalMemory, NumberOfProcesses, LastBootUpTime from Win32_OperatingSystem",

            "select Name, FileSystem, Size, FreeSpace from Win32_LogicalDisk",
            "select HotFixID, InstalledOn from Win32_QuickFixEngineering",
            "select * from Win32_ComputerSystem",
            "select Description, EstimatedChargeRemaining, BatteryStatus from Win32_Battery",
            "select Caption from Win32_TimeZone",
            "select SerialNumber from Win32_BaseBoard",
            "select IPEnabled, IPAddress, MacAddress from Win32_NetworkAdapterConfiguration"
        ]
        ) + smb_shell_commands(BAD_CONFIGURATIONS_COMMANDS)

    def handle_result(self, device, executer_info, result, adapterdata_device: DeviceAdapter):
        super().handle_result(device, executer_info, result, adapterdata_device)
        # Put Results
        win32_processor = result[0]
        win32_bios = result[1]
        win32_operatingsystem = result[2]
        win32_logicaldisk = result[3]
        win32_quickfixengineering = result[4]
        win32_computersystem = result[5]
        win32_battery = result[6]
        win32_timezone = result[7]
        win32_baseboard = result[8]
        win32_networkadapterconfiguration = result[9]
        bad_configuration_lsa = result[10]

        # Win32_Processor
        try:
            assert is_wmi_answer_ok(win32_processor), "WMI Answer has an exception"
            for cpu in win32_processor["data"]:
                architecture = cpu.get('Architecture')
                if architecture is not None:
                    architecture = {0: "x86", 1: "MIPS", 2: "Alpha", 3: "PowerPC",
                                    5: "ARM", 6: "ia64", 9: "x64"}.get(architecture)

                max_clock_speed_ghz = cpu.get('MaxClockSpeed')
                if max_clock_speed_ghz is not None:
                    max_clock_speed_ghz = float(round(max_clock_speed_ghz / 1024, 2))

                adapterdata_device.add_cpu(
                    name=cpu.get('Name'),
                    bitness=cpu.get('AddressWidth'),
                    cores=cpu.get('NumberOfCores'),
                    load_percentage=cpu.get('LoadPercentage'),
                    architecture=architecture,
                    ghz=max_clock_speed_ghz
                )
        except Exception:
            self.logger.exception(f"Couldn't handle Win32_Processor: {win32_processor}")

        try:
            # Bios
            assert is_wmi_answer_ok(win32_bios), "WMI Answer has an exception"
            win32_bios = win32_bios["data"][0]
            adapterdata_device.bios_version = win32_bios.get('SMBIOSBIOSVersion')
            adapterdata_device.bios_serial = win32_bios.get('SerialNumber')
        except Exception:
            self.logger.exception(f"Win32_BIOS {win32_bios}")

        try:
            # Device
            assert is_wmi_answer_ok(win32_computersystem), "WMI Answer has an exception"
            win32_computersystem = win32_computersystem["data"][0]
            adapterdata_device.device_model_family = win32_computersystem.get("SystemFamily")
            adapterdata_device.device_model = win32_computersystem.get("Model")
            adapterdata_device.device_manufacturer = win32_computersystem.get("Manufacturer")
            adapterdata_device.hostname = win32_computersystem.get("DNSHostName")

            # Number Of Processors & Cores
            total_number_of_processors = win32_computersystem.get("NumberOfProcessors")
            if total_number_of_processors is not None:
                adapterdata_device.total_number_of_physical_processors = int(total_number_of_processors)

            total_number_of_cores = win32_computersystem.get("NumberOfLogicalProcessors")
            if total_number_of_cores is not None:
                adapterdata_device.total_number_of_cores = int(total_number_of_cores)

            # Users
            adapterdata_device.current_logged_user = win32_computersystem.get("UserName")
            adapterdata_device.domain = win32_computersystem.get("Domain")
            partofdomain = win32_computersystem.get("PartOfDomain")
            if partofdomain is not None:
                adapterdata_device.part_of_domain = str2bool(partofdomain)

            # Type of system
            pc_system_type = win32_computersystem.get("PCSystemType")
            if pc_system_type is not None:
                adapterdata_device.pc_type = {0: "Unspecified", 1: "Desktop", 2: "Laptop or Tablet", 3: "Workstation",
                                              4: "Enterprise Server", 5: "SOHO Server", 6: "Appliance PC",
                                              7: "Performance Server", 8: "Maximum"}.get(pc_system_type)
        except Exception:
            self.logger.exception(f"Win32_ComputerSystem {win32_computersystem}")

        # We don't always have baseboards, for some reason. so lets try.
        try:
            assert is_wmi_answer_ok(win32_baseboard), "WMI Answer has an exception"
            if len(win32_baseboard["data"]) > 0:
                sn = win32_baseboard["data"][0].get("SerialNumber")
                if sn is not None and sn != "None":
                    # Yep, it happens. Sometimes wmi returns "None" as a string.
                    adapterdata_device.device_serial = sn
        except Exception:
            self.logger.exception(f"Can't use Win32_BaseBoard {win32_baseboard}")

        # Win32_OperatingSystem
        try:
            assert is_wmi_answer_ok(win32_operatingsystem), "WMI Answer has an exception"
            win32_operatingsystem = win32_operatingsystem["data"][0]
            os_caption = win32_operatingsystem.get("Caption")
            if os_caption is not None:
                adapterdata_device.figure_os(os_caption)
            else:
                # We put some os just so adapterdata_device.os will be initialized
                adapterdata_device.figure_os("")

            # This could be 0 or None, in both cases we want to gracefull catch that.
            try:
                install_date = win32_operatingsystem.get("InstallDate")
                if install_date is not None and install_date != "0":
                    adapterdata_device.os.install_date = wmi_date_to_datetime(install_date)
            except Exception:
                self.logger.exception(f"Exception inserting InstallDate {install_date}:")

            # Same here
            try:
                boot_time = win32_operatingsystem.get("LastBootUpTime")
                if boot_time is not None and boot_time != "0":
                    adapterdata_device.boot_time = wmi_date_to_datetime(boot_time)
            except Exception:
                self.logger.exception(f"Exception inserting LastBootUpTime {boot_time}")

            os_version = win32_operatingsystem.get("Version", "").split(".")
            try:
                adapterdata_device.os.major = int(os_version[0])
            except Exception:
                self.logger.exception("Can't set OS Major")

            try:
                adapterdata_device.os.minor = int(os_version[1])
            except Exception:
                self.logger.exception("Can't set OS Minor")

            adapterdata_device.os.build = str(win32_operatingsystem.get("BuildNumber"))

            # Sometimes, total_ram / free_ram return as 0 and then we might have wrong info here and even
            # division in 0 exception
            total_ram = win32_operatingsystem.get("TotalVisibleMemorySize")
            if total_ram is not None and total_ram > 0:
                adapterdata_device.total_physical_memory = float(round(total_ram / (1024 ** 2), 2))

            free_ram = win32_operatingsystem.get("FreePhysicalMemory")
            if free_ram is not None and free_ram > 0:
                adapterdata_device.free_physical_memory = float(round(free_ram / (1024 ** 2), 2))

            if total_ram is not None and free_ram is not None and total_ram > 0 and free_ram > 0:
                adapterdata_device.physical_memory_percentage = float(
                    round((total_ram - free_ram) / total_ram * 100, 2)
                )

            number_of_processes = win32_operatingsystem.get("NumberOfProcesses")
            if number_of_processes is not None:
                adapterdata_device.number_of_processes = int(number_of_processes)

        except Exception:
            self.logger.exception(f"Win32_OperatingSystem {win32_operatingsystem}")

        # Win32_LogicalDisk
        try:
            assert is_wmi_answer_ok(win32_logicaldisk), "WMI Answer has an exception"
            for ld in win32_logicaldisk["data"]:
                total_size = ld.get("Size")
                if total_size is not None:
                    total_size = float(total_size / (1024 ** 3))

                free_size = ld.get("FreeSpace")
                if free_size is not None:
                    free_size = float(free_size / (1024 ** 3))

                adapterdata_device.add_hd(
                    path=ld.get("Name"),
                    total_size=total_size,
                    free_size=free_size,
                    file_system=ld.get("FileSystem")
                )

        except Exception:
            self.logger.exception(f"Win32_LogicalDisk {win32_logicaldisk}")

        try:
            assert is_wmi_answer_ok(win32_quickfixengineering), "WMI Answer has an exception"
            for qfe in win32_quickfixengineering["data"]:
                installed_on = qfe.get("InstalledOn")
                hotfix_id = qfe.get("HotFixID")

                if installed_on is not None and installed_on != "0":
                    try:
                        installed_on = parse_date(installed_on)
                    except Exception:
                        self.logger.exception(f"Can't parse installed_on {installed_on}, setting to None")
                        installed_on = None
                else:
                    # We better have installed_on None and not "0".
                    installed_on = None

                if hotfix_id.lower() != "file 1":
                    # This is a phenomena that happens on some windows devices, we need to ignore it.
                    # https://social.technet.microsoft.com/Forums/exchange/en-US/ac717bfa-8ca4-474e-806c-e0a21e67482d/wh
                    # at-does-it-mean-when-win32quickfixengineeringhotfixid-is-set-to-file-1?forum=winserverManagement
                    adapterdata_device.add_security_patch(
                        security_patch_id=hotfix_id,
                        installed_on=installed_on
                    )
        except Exception:
            self.logger.exception(f"Win32_QuickFixEngineering {win32_quickfixengineering}")

        try:
            assert is_wmi_answer_ok(win32_battery), "WMI Answer has an exception"
            for battery in win32_battery["data"]:
                battery_status = battery.get("BatteryStatus")
                if battery_status is not None:
                    battery_status = {
                        1: "Not Charging",
                        2: "Connected to AC",
                        3: "Fully Charged",
                        4: "Low",
                        5: "Critical",
                        6: "Charging",
                        7: "Charging and High",
                        8: "Charging and Low",
                        9: "Charging and Critical",
                        10: "Undefined",
                        11: "Partially Charged"}.get(battery_status)

                battery_percentage = adapterdata_device.get("EstimatedChargeRemaining")
                if battery_percentage is not None:
                    battery_percentage = int(battery_percentage)

                adapterdata_device.add_battery(
                    status=battery_status,
                    percentage=battery_percentage
                )
        except Exception:
            self.logger.exception(f"Win32_Battery {win32_battery}")

        try:
            assert is_wmi_answer_ok(win32_timezone), "WMI Answer has an exception"
            win32_timezone = win32_timezone["data"][0]
            adapterdata_device.time_zone = win32_timezone.get("Caption")
        except Exception:
            self.logger.exception(f"Win32_TimeZone {win32_timezone}")

        # Add network interfaces
        try:
            assert is_wmi_answer_ok(win32_networkadapterconfiguration), "WMI Answer has an exception"
            for nic in win32_networkadapterconfiguration["data"]:
                ip_enabled = nic.get("IPEnabled")
                if ip_enabled is not None and bool(ip_enabled) is True:
                    adapterdata_device.add_nic(
                        mac=nic.get("MACAddress"),
                        ips=nic.get("IPAddress")
                    )
        except Exception:
            self.logger.exception(f"Win32_NetworkAdapterConfiguration {win32_networkadapterconfiguration}")

        # Bad Configurations Config

        try:
            assert is_wmi_answer_ok(bad_configuration_lsa), "WMI Answer has an exception"
            data = reg_view_output_to_dict(bad_configuration_lsa["data"])

            adapterdata_device.ad_bad_config_no_lm_hash = reg_view_parse_int(data.get("nolmhash"))
            adapterdata_device.ad_bad_config_force_guest = reg_view_parse_int(data.get("forceguest"))
            adapterdata_device.ad_bad_config_authentication_packages = data.get("authentication packages")
            adapterdata_device.ad_bad_config_lm_compatibility_level = reg_view_parse_int(
                data.get("lmcompatibilitylevel"))
            adapterdata_device.ad_bad_config_disabled_domain_creds = reg_view_parse_int(data.get("disableddomaincreds"))
            adapterdata_device.ad_bad_config_secure_boot = reg_view_parse_int(data.get("secureboot"))

        except Exception:
            self.logger.exception(f"bad_configuration_lsa is not ok: {bad_configuration_lsa}")

        return True
