"""
Using wmi queries, determines basic computer info
"""
from .general_info_subplugin import GeneralInfoSubplugin
from .wmi_utils import wmi_date_to_datetime


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
            {"type": "query", "args": ["select Name, AddressWidth, NumberOfCores, Architecture from Win32_Processor"]},
            {"type": "query", "args": ["select SMBIOSBIOSVersion, SerialNumber from Win32_BIOS"]},
            {"type": "query", "args": [
                "select Caption, Description, Version, BuildNumber, InstallDate, TotalVirtualMemorySize, "
                "FreeVirtualMemory, NumberOfProcesses from Win32_OperatingSystem"]},
            {"type": "query", "args": ["select Name, FileSystem, Size, FreeSpace from Win32_LogicalDisk"]},
            {"type": "query", "args": ["select HotFixID, InstalledOn from Win32_QuickFixEngineering"]},
            {"type": "query", "args": ["select Manufacturer, Product, SerialNumber from Win32_BaseBoard"]},
            {"type": "query", "args": [
                "select Description, EstimatedChargeRemaining, BatteryStatus from Win32_Battery"]}
        ]

    def handle_result(self, device, executer_info, result):
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
                        "Architecture": {0: "x86", 1: "MIPS", 2: "Alpha", 3: "PowerPC",
                                         5: "ARM", 6: "ia64", 9: "x64"}[cpu['Architecture']]
                    }
                )
        except Exception:
            basic['CPUs'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_Processor: {result[0]}")

        # Win32_BIOS
        try:
            basic['Hardware'] = {
                "BIOS Version": result[1][0]['SMBIOSBIOSVersion'],
                "BIOS Serial": result[1][0]['SerialNumber']
            }
        except Exception:
            basic['Hardware'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_BIOS and Win32_Hardware: {result[1]}")

        # Win32_BaseBoard
        try:
            basic['BaseBoard'] = []
            for bb in result[5]:
                basic['BaseBoard'].append(
                    {
                        "Baseboard Manufacturer": bb["Manufacturer"],
                        "Baseboard Model": bb["Product"],
                        "Baseboard Serial": bb["SerialNumber"]
                    }
                )
        except Exception:
            basic['BaseBoard'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_BaseBoard: {result[5]}")

        # Win32_OperatingSystem
        try:
            basic['Operating System'] = {
                "Name": result[2][0]['Caption'],
                # e.g. "Avidor's PC" - whatever you see in "My Computer"
                "Description": result[2][0]['Description'],
                "Version": result[2][0]['Version'],
                "Build Number": result[2][0]['BuildNumber'],
                "Install Date": str(wmi_date_to_datetime(result[2][0]['InstallDate'])),
                "Total Virtual Memory (MB)": result[2][0]['TotalVirtualMemorySize'] / 1024,
                "Free Virtual Memory (MB)": result[2][0]['FreeVirtualMemory'] / 1024,
                "Number Of Processes": result[2][0]['NumberOfProcesses']
            }
        except Exception:
            basic['Operating System'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_OperatingSystem: {result[2]}")

        # Win32_LogicalDisk
        try:
            basic['Logical Disks'] = []
            for i, ld in enumerate(result[3]):
                basic['Logical Disks'].append(
                    {
                        "Name": ld["Name"],
                        "File System": ld["FileSystem"],
                        "Size (MB)": ld["Size"] / (1024 ** 3),
                        "Free Space (GB)": ld["FreeSpace"] / (1024 ** 3)
                    }
                )
        except Exception:
            basic['Logical Disks'] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_LogicalDisk: {result[3]}")

        # Win32_QuickFixEngineering
        try:
            hot_fixes = []
            for qfe in result[4]:
                hot_fixes.append({
                    "HotFix ID": qfe['HotFixID'],
                    "Installed On": qfe['InstalledOn']
                })
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
            else:
                basic["Battery"] = "No Battery"
        except Exception:
            basic["Battery"] = "Unknown Exception"
            self.logger.exception(f"Couldn't handle Win32_Battery: {result[6]}")

        self.plugin_base.add_data_to_device(
            (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), "Basic Info", basic)

        self.plugin_base.add_data_to_device(
            (executer_info["adapter_unique_name"], executer_info["adapter_unique_id"]), "Hot Fixes", hot_fixes)
