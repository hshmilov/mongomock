"""
Using wmi queries, determines basic computer info
"""
from .general_info_subplugin import GeneralInfoSubplugin
from .wmi_utils import wmi_date_to_datetime
from dateutil import parser
import datetime
from axonius.device import Device


class GetBasicComputerInfo(GeneralInfoSubplugin):
    """
    Gets all basic computer info on that machine.
    """

    def __init__(self, plugin_base_delegate):
        """
        initialization.
        :param plugin_base_delegate: the "self" of a relevant plugin base.
        """
        super().__init__(plugin_base_delegate)
        self.users = {}  # a cache var for storing users from adapters.
        self.logger.info("Initialized BasicComputerInfo plugin")

    def get_wmi_commands(self):
        return [
            {"type": "query", "args": ["select Name, AddressWidth, NumberOfCores, LoadPercentage, "
                                       "Architecture, MaxClockSpeed from Win32_Processor"]},
            {"type": "query", "args": ["select SMBIOSBIOSVersion, SerialNumber from Win32_BIOS"]},
            {"type": "query", "args": [
                "select Caption, Description, Version, BuildNumber, InstallDate, "
                "TotalVisibleMemorySize, FreePhysicalMemory, "
                "NumberOfProcesses, LastBootUpTime from Win32_OperatingSystem"]},
            {"type": "query", "args": ["select Name, FileSystem, Size, FreeSpace from Win32_LogicalDisk"]},
            {"type": "query", "args": ["select HotFixID, InstalledOn from Win32_QuickFixEngineering"]},
            {"type": "query", "args": ["select * from Win32_ComputerSystem"]},
            {"type": "query", "args": [
                "select Description, EstimatedChargeRemaining, BatteryStatus from Win32_Battery"]},
            {"type": "query", "args": [
                "select Caption, Bias from Win32_TimeZone"]},
            {"type": "query", "args": ["select SerialNumber from Win32_BaseBoard"]},
        ]

    def handle_result(self, device, executer_info, result, adapterdata_device: Device):
        # Assemble a couple of tags representing the data here.
        basic = dict()

        # Win32_Processor
        try:
            basic['CPUs'] = []
            for i, cpu in enumerate(result[0]):
                basic['CPUs'].append(
                    {
                        "CPU Num": i,
                        "Name": cpu['Name'],
                        "Bitness": cpu['AddressWidth'],
                        "Cores": cpu['NumberOfCores'],
                        "Load Percentage": cpu['LoadPercentage'],
                        "Max Clock Speed (GHz)": round(cpu['MaxClockSpeed'] / 1024, 2),   # This comes in mhz by default
                        "Architecture": {0: "x86", 1: "MIPS", 2: "Alpha", 3: "PowerPC",
                                         5: "ARM", 6: "ia64", 9: "x64"}[cpu['Architecture']]
                    })

                last = basic['CPUs'][-1]   # What we just instrted
                adapterdata_device.add_cpu(
                    name=str(last["Name"]),
                    bitness=int(last["Bitness"]),
                    cores=int(last["Cores"]),
                    load_percentage=int(last["Load Percentage"]),
                    architecture=str(last["Architecture"]),
                    ghz=float(last["Max Clock Speed (GHz)"])
                )
        except Exception:
            basic['CPUs'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_Processor: {result[0]}")

        # Win32_BIOS, Win32_ComputerSystem, Win32_BaseBoard
        try:
            basic['Hardware'] = {
                "BIOS Version": result[1][0]['SMBIOSBIOSVersion'],
                "BIOS Serial": result[1][0]['SerialNumber'],
                "Device Manufacturer": result[5][0].get("Manufacturer", "Unknown"),
                "Device Model": result[5][0].get("Model", "Unknown"),
                "Device Model Family": result[5][0].get("SystemFamily", "Unknown"),
                "Total Number Of Physical Processors": result[5][0].get("NumberOfProcessors", "Unknown"),
                "Total Number Of Logical Processors": result[5][0].get("NumberOfLogicalProcessors", "Unknown")
            }

            adapterdata_device.bios_version = str(basic['Hardware']['BIOS Version'])
            adapterdata_device.bios_serial = str(basic['Hardware']['BIOS Serial'])

            # For some reason, which might be only on ec2, this sometimes fail with DCERPCSessionError.
            if basic['Hardware']['Device Manufacturer'] != "Unknown":
                adapterdata_device.device_manufacturer = str(basic['Hardware']['Device Manufacturer'])
                adapterdata_device.device_model = str(basic['Hardware']['Device Model'])
                adapterdata_device.device_model_family = str(basic['Hardware']['Device Model Family'])
                adapterdata_device.total_number_of_physical_processors = \
                    int(basic["Hardware"]['Total Number Of Physical Processors'])
                adapterdata_device.total_number_of_logical_Processors = \
                    int(basic["Hardware"]['Total Number Of Logical Processors'])
            else:
                self.logger.error(f"Noice that we do not take data from Win32_ComputerSystem, since there is"
                                  f" an excpetion there: {result[5]}")

        except Exception:
            basic['Hardware'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_BIOS, Win32_Hardware, Win32_ComputerSystem: {result[1]}")

        # We don't always have baseboards, for some reason. so lets try.
        if len(result[8]) > 0:
            basic["Hardware"]["Device Manufacturer Serial"] = result[8][0]["SerialNumber"]
            adapterdata_device.device_serial = str(basic['Hardware']['Device Manufacturer Serial'])

        # Win32_ComputerSystem
        try:
            # For some reason, which might be only on ec2, this sometimes fail with DCERPCSessionError.
            if basic['Hardware']['Device Manufacturer'] != "Unknown":
                basic['User'] = {
                    "Currently Logged User": result[5][0]["UserName"] if type(result[5][0]["UserName"]) == str else "None",
                    "Domain": result[5][0]["Domain"],
                    "Part Of Domain": result[5][0]["PartOfDomain"]
                }

                adapterdata_device.current_logged_user = str(basic['User']['Currently Logged User'])
                adapterdata_device.domain = str(basic['User']['Domain'])
                adapterdata_device.part_of_domain = bool(basic['User']['Part Of Domain'])
        except Exception:
            basic['User'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_ComputerSystem: {result[1]}")

        # Win32_OperatingSystem
        try:
            basic['Operating System'] = {
                "Name": result[2][0]['Caption'],
                # e.g. "Avidor's PC" - whatever you see in "My Computer"
                "Description": result[2][0]['Description'],
                "Version": result[2][0]['Version'],
                "Build Number": result[2][0]['BuildNumber'],
                "Install Date": wmi_date_to_datetime(result[2][0]['InstallDate']),
                "Last Boot Up Time": wmi_date_to_datetime(result[2][0]['LastBootUpTime']),
                "Total RAM (GB)": round(result[2][0]['TotalVisibleMemorySize'] / (1024 ** 2), 2),
                "Free RAM (GB)": round(result[2][0]['FreePhysicalMemory'] / (1024 ** 2), 2),
                "RAM Usage (%)": round((((result[2][0]['TotalVisibleMemorySize'] - result[2][0]['FreePhysicalMemory'])
                                         / result[2][0]['TotalVisibleMemorySize'])) * 100, 2),
                "Number Of Processes": result[2][0]['NumberOfProcesses']
            }

            # Note that we need to figure out the os first, to create the DeviceOS object. Only afterwards
            # we can access its fields.
            adapterdata_device.figure_os(basic['Operating System']['Name'])
            adapterdata_device.os.install_date = basic['Operating System']['Install Date']  # datetime
            adapterdata_device.boot_time = basic['Operating System']['Last Boot Up Time']   # datetime
            adapterdata_device.total_physical_memory = float(basic['Operating System']['Total RAM (GB)'])
            adapterdata_device.free_physical_memory = float(basic['Operating System']['Free RAM (GB)'])
            adapterdata_device.physical_memory_percentage = float(basic['Operating System']['RAM Usage (%)'])
            adapterdata_device.number_of_processes = int(basic['Operating System']['Number Of Processes'])

            # Build returns as a string and not an int, i'm afraid it could be an str...
            try:
                adapterdata_device.os.build = int(basic['Operating System']['Build Number'])
            except:
                pass

        except Exception:
            basic['Operating System'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_OperatingSystem: {result[2]}")

        # Win32_LogicalDisk
        try:
            basic['Logical Disks'] = []
            for ld in result[3]:
                basic['Logical Disks'].append(
                    {
                        "Name": ld["Name"],
                        "File System": ld["FileSystem"],
                        "Size (MB)": ld["Size"] / (1024 ** 3),
                        "Free Space (GB)": ld["FreeSpace"] / (1024 ** 3)
                    }
                )

                last = basic['Logical Disks'][-1]
                adapterdata_device.add_hd(
                    path=str(last["Name"]),
                    total_size=float(last["Size (MB)"]),
                    free_size=float(last["Free Space (GB)"]),
                    file_system=last["File System"] if type(last["File System"]) == str else "Unknown"
                )

        except Exception:
            basic['Logical Disks'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_LogicalDisk: {result[3]}")

        # Win32_QuickFixEngineering
        try:
            hot_fixes = []
            for qfe in result[4]:
                try:
                    installedon_datetime = parser.parse(qfe['InstalledOn'])
                except:
                    installedon_datetime = datetime.datetime(1, 1, 1)   # Unknown date...

                hot_fixes.append({
                    "HotFix ID": qfe['HotFixID'],
                    "Installed On": installedon_datetime
                })

                last = hot_fixes[-1]
                adapterdata_device.add_security_patch(
                    security_patch_id=str(last["HotFix ID"]),
                    installed_on=last["Installed On"]   # datetime
                )
        except Exception:
            hot_fixes = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Hot Fixes: {result[4]}")

        # Win32_Battery. Assuming one battery..
        try:
            if len(result[6]) == 1:
                basic["Battery"] = {
                    "Description": result[6][0]["Description"],
                    "Percentage": result[6][0]["EstimatedChargeRemaining"],
                    "Status": {
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
                        11: "Partially Charged"}[result[6][0]["BatteryStatus"]]
                }

                adapterdata_device.battery.percentage = int(basic["Battery"]["Percentage"])
                adapterdata_device.battery.status = str(basic["Battery"]["Status"])
            else:
                basic["Battery"] = "No Battery"
        except Exception:
            basic["Battery"] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_Battery: {result[6]}")

        try:
            basic["Time Zone"] = {
                "Time Zone": result[7][0]["Caption"],
                "Bias (in minutes)": result[7][0]["Bias"]
            }

            adapterdata_device.time_zone = str(basic["Time Zone"]["Time Zone"])
        except Exception:
            basic["Timezone"] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_TimeZone: {result[7]}")

        self.plugin_base.add_data_to_device(
            (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), "Basic Info", basic)

        self.plugin_base.add_data_to_device(
            (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), "Hot Fixes", hot_fixes)
