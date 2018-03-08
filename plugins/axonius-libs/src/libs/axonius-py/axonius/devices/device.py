import datetime
import typing

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.parsing_utils import figure_out_os, format_mac, format_ip, format_ip_raw
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict

"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class DeviceOS(SmartJsonClass):
    """ A definition for the json-scheme for an OS (of a device) """
    type = Field(str, 'OS', enum=['Windows', 'Linux', 'OS X', 'iOS', 'Android', 'FreeBSD', 'VMWare'])
    distribution = Field(str, 'OS Distribution')
    bitness = Field(int, 'OS Bitness', enum=[32, 64])
    build = Field(str, 'OS Build')  # aka patch level
    install_date = Field(datetime.datetime, "OS Install Date")

    major = Field(int, 'OS Major')
    minor = Field(int, 'OS Minor')


class NetworkInterface(SmartJsonClass):
    """ A definition for the json-scheme for a network interface """
    mac = Field(str, 'Mac', converter=format_mac)
    ips = ListField(str, 'IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    ips_raw = ListField(str, description='Number representation of the IP, useful for filtering by range',
                        converter=format_ip_raw)


class DeviceHD(SmartJsonClass):
    """ A definition for hard drives on that device. On windows, that would be a drive.
    On linux and mac, we need to think what it is (not sure its mounts...) """

    path = Field(str, "HD Path")
    total_size = Field(float, "HD Size (GB)")
    free_size = Field(float, "HD Free Size (GB)")
    is_encrypted = Field(bool, "HD Encrypted")
    file_system = Field(str, "HD Filesystem")


class DeviceCPU(SmartJsonClass):
    """ A definition for cpu's """

    name = Field(str, "CPU Description")
    bitness = Field(int, "CPU Bitness", enum=[32, 64])
    cores = Field(int, "CPU Cores")
    load_percentage = Field(int, "CPU Load Percentage")
    architecture = Field(str, "CPU Architecture", enum=["x86", "x64", "MIPS", "Alpha", "PowerPC", "ARM", "ia64"])
    ghz = Field(float, "CPU Clockspeed (GHZ)")


class DeviceBattery(SmartJsonClass):
    """ A definition for a battery"""

    percentage = Field(int, "Battery Percentage")
    status = Field(str, "Battery Status", enum=["Not Charging", "Connected to AC", "Fully Charged", "Low", "Critical",
                                                "Charging", "Charging and High", "Charging and Low",
                                                "Charging and Critical", "Undefined", "Partially Charged"])


class DeviceUser(SmartJsonClass):
    """ A definition for users known by this device"""

    username = Field(str, "Known User")
    last_use_date = Field(datetime.datetime)
    is_local = Field(bool, "Is User Local")


class DeviceSecurityPatch(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    security_patch_id = Field(str, "Security Patch Name")
    installed_on = Field(datetime.datetime)


class DeviceInstalledSoftware(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    vendor = Field(str, "Software Vendor")
    name = Field(str, "Software Name")
    version = Field(str)


class Device(SmartJsonClass):
    """ A definition for the json-scheme for a Device """

    pretty_id = Field(str, 'Axonius Name')
    id = Field(str, 'ID')
    name = Field(str, 'Asset Name')
    hostname = Field(str, 'Host Name')
    os = Field(DeviceOS)
    last_seen = Field(datetime.datetime, 'Last Seen')
    network_interfaces = ListField(NetworkInterface, 'Network Interfaces')
    scanner = Field(bool, 'Scanner')
    part_of_domain = Field(bool, "Part Of Domain")
    domain = Field(str, "Domain")
    last_used_users = ListField(str, "Last Used User")
    current_logged_user = Field(str, "Currently Logged User")
    installed_software = ListField(DeviceInstalledSoftware, "Installed Software")
    users = ListField(DeviceUser, "Users")
    security_patches = ListField(DeviceSecurityPatch, "Security Patch")
    device_manufacturer = Field(str, "Device Manufacturer")
    device_model = Field(str, "Device Model")
    device_model_family = Field(str, "Device Model Family")
    device_serial = Field(str, "Device Manufacturer Serial")
    pc_type = Field(str, "PC Type", enum=["Unspecified", "Desktop", "Laptop or Tablet", "Workstation",
                                          "Enterprise Server", "SOHO Server", "Appliance PC", "Performance Server",
                                          "Maximum"])
    number_of_processes = Field(int, "Number Of Processes")
    hard_drives = ListField(DeviceHD, "Hard Drives")
    cpus = ListField(DeviceCPU, "CPUs")
    boot_time = Field(datetime.datetime, 'Boot Time')
    time_zone = Field(str, 'Time Zone')
    bios_version = Field(str, "Bios Version")
    bios_serial = Field(str, "Bios Serial")
    total_physical_memory = Field(float, "Total RAM (GB)")
    free_physical_memory = Field(float, "Free RAM (GB)")
    physical_memory_percentage = Field(float, "RAM Usage (%)")
    total_number_of_physical_processors = Field(int, "Total Physical Processors")
    total_number_of_cores = Field(int, "Total Cores")
    batteries = ListField(DeviceBattery, "Battery")

    required = ['name', 'hostname', 'os', 'network_interfaces']

    def __init__(self, adapter_fields: typing.MutableSet[str], adapter_raw_fields: typing.MutableSet[str]):
        """ The adapter_fields and adapter_raw_fields will be auto-populated when new fields are set. """
        super().__init__()
        # do not pass kwargs to constructor before setting up self._adapter_fields
        # because its supposed to populate the names of the fields into it - see _define_new_name override here
        self._adapter_fields = adapter_fields
        self._adapter_raw_fields = adapter_raw_fields
        self._raw_data = {}  # will hold any extra raw fields that are associated with this device.

    def _define_new_name(self, name: str):
        if name.startswith('raw.'):
            target_field_list = self._adapter_raw_fields
        else:
            target_field_list = self._adapter_fields
        target_field_list.add(name)

    def set_raw(self, raw_data: dict):
        """ Sets the raw fields associated with this device and also updates adapter_raw_fields.
            Use only this function because it also fixes '.' in the keys such that it will work on MongoDB.
        """
        assert isinstance(raw_data, dict)
        raw_data = escape_dict(raw_data)
        self._raw_data = raw_data
        self._dict['raw'] = self._raw_data
        self._extend_names('raw', raw_data)

    def add_nic(self, mac=None, ips=None, logger=None):
        """
        Add a new network interface card to this device.
        :param mac: the mac
        :param ips: an IP list
        :param logger: a python logger, if provided will record and suppress all parsing exceptions
        """
        nic = NetworkInterface()
        if mac is not None:
            try:
                nic.mac = mac
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid mac: {repr(mac)}')
        if ips is not None:
            try:
                ips_iter = iter(ips)
            except TypeError:
                if logger is None:
                    raise
                logger.exception(f'Invalid ips: {repr(ips)}')
            else:
                for ip in ips_iter:
                    try:
                        nic.ips.append(ip)
                        nic.ips_raw.append(ip)
                    except (ValueError, TypeError):
                        if logger is None:
                            raise
                        logger.exception(f'Invalid ip: {repr(ip)}')
        self.network_interfaces.append(nic)

    def figure_os(self, os_string):
        os_dict = figure_out_os(os_string)
        if os_dict is None:
            return
        self.os = DeviceOS(**os_dict)

    def add_battery(self, **kwargs):
        self.batteries.append(DeviceBattery(**kwargs))

    def add_hd(self, **kwargs):
        self.hard_drives.append(DeviceHD(**kwargs))

    def add_cpu(self, **kwargs):
        self.cpus.append(DeviceCPU(**kwargs))

    def add_users(self, **kwargs):
        self.users.append(DeviceUser(**kwargs))

    def add_security_patch(self, **kwargs):
        self.security_patches.append(DeviceSecurityPatch(**kwargs))

    def add_installed_software(self, **kwargs):
        self.installed_software.append(DeviceInstalledSoftware(**kwargs))


NETWORK_INTERFACES_FIELD = Device.network_interfaces.name
SCANNER_FIELD = Device.scanner.name
LAST_SEEN_FIELD = Device.last_seen.name
OS_FIELD = Device.os.name

MAC_FIELD = NetworkInterface.mac.name
IPS_FIELD = NetworkInterface.ips.name
