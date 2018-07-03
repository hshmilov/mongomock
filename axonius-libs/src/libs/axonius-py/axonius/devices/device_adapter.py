import logging
logger = logging.getLogger(f"axonius.{__name__}")
import datetime
import typing

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.utils.parsing import figure_out_os, format_mac, format_ip, format_ip_raw, format_subnet, \
    get_manufacturer_from_mac, normalize_mac
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict
from enum import Enum, auto
"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class DeviceRunningState(Enum):
    """
    Defines the state of device. i.e. if it is turned on or not
    """

    def _generate_next_value_(name, *args):
        return name

    """
    Device is on
    """
    TurnedOn = auto()
    """
    Device is off
    """
    TurnedOff = auto()
    """
    Device is suspended, i.e. hibenate
    """
    Suspended = auto()
    """
    Device is in the process of shutting down
    """
    ShuttingDown = auto()
    """
    State is unknown
    """
    Unknown = auto()


class DeviceAdapterOS(SmartJsonClass):
    """ A definition for the json-scheme for an OS (of a device) """
    type = Field(str, 'Type', enum=['Windows', 'Linux', 'OS X', 'iOS',
                                    'Android', 'FreeBSD', 'VMWare', 'Cisco', 'Mikrotik'])
    distribution = Field(str, 'Distribution')
    bitness = Field(int, 'Bitness', enum=[32, 64])
    build = Field(str, 'Build')  # aka patch level
    sp = Field(str, 'Service Pack')
    install_date = Field(datetime.datetime, "Install Date")

    major = Field(int, 'Major')
    minor = Field(int, 'Minor')


class DeviceAdapterNetworkInterface(SmartJsonClass):
    """ A definition for the json-scheme for a network interface """
    name = Field(str, 'Iface Name')
    mac = Field(str, 'Mac', converter=format_mac)
    manufacturer = Field(str, 'Manufacturer')
    ips = ListField(str, 'IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    subnets = ListField(str, 'Subnets', converter=format_subnet, json_format=JsonStringFormat.subnet,
                        description='A list of subnets in ip format, that correspond the IPs')
    ips_raw = ListField(str, description='Number representation of the IP, useful for filtering by range',
                        converter=format_ip_raw)


class DeviceAdapterHD(SmartJsonClass):
    """ A definition for hard drives on that device. On windows, that would be a drive.
    On linux and mac, we need to think what it is (not sure its mounts...) """

    path = Field(str, "Path")
    total_size = Field(float, "Size (GB)")
    free_size = Field(float, "Free Size (GB)")
    is_encrypted = Field(bool, "Encrypted")
    file_system = Field(str, "Filesystem")


class DeviceAdapterCPU(SmartJsonClass):
    """ A definition for cpu's """

    name = Field(str, "Description")
    bitness = Field(int, "Bitness", enum=[32, 64])
    cores = Field(int, "Cores")
    load_percentage = Field(int, "Load Percentage")
    architecture = Field(str, "Architecture", enum=["x86", "x64", "MIPS", "Alpha", "PowerPC", "ARM", "ia64"])
    ghz = Field(float, "Clockspeed (GHZ)")


class DeviceAdapterBattery(SmartJsonClass):
    """ A definition for a battery"""

    percentage = Field(int, "Percentage")
    status = Field(str, "Status", enum=["Not Charging", "Connected to AC", "Fully Charged", "Low", "Critical",
                                        "Charging", "Charging and High", "Charging and Low",
                                        "Charging and Critical", "Undefined", "Partially Charged"])


class DeviceAdapterUser(SmartJsonClass):
    """ A definition for users known by this device"""

    user_sid = Field(str, "SID")
    username = Field(str, "Username")
    last_use_date = Field(datetime.datetime, 'Last Use Time')
    is_local = Field(bool, "Is Local")
    is_disabled = Field(bool, "Is Disabled")

    # Where did this user really come from?
    origin_unique_adapter_name = Field(str)
    origin_unique_adapter_data_id = Field(str)
    origin_unique_adapter_client = Field(str)


class DeviceAdapterConnectedHardware(SmartJsonClass):
    """ A definition for connected devices of this device"""

    name = Field(str, "Name")
    manufacturer = Field(str, "Manufacturer")
    hw_id = Field(str, "ID")


class DeviceAdapterSecurityPatch(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    security_patch_id = Field(str, "Security Patch Name")
    installed_on = Field(datetime.datetime)


class DeviceAdapterMsrcAvailablePatch(SmartJsonClass):
    """ A definition for the json-schema for an available msrc patch"""
    title = Field(str, "Title")
    security_bulletin_ids = ListField(str, "Security Bulletin ID's")
    kb_article_ids = ListField(str, "KB Article ID's")
    msrc_severity = Field(str, "MSRC Severity")
    patch_type = Field(str, "Type", enum=["Software", "Driver"])
    categories = ListField(str, "Categories")
    publish_date = Field(datetime.datetime, "Publish Date")


class DeviceAdapterLocalAdmin(SmartJsonClass):
    """A definition for local admins list"""

    admin_name = Field(str, "Name of user or group")
    admin_type = Field(str, "Admin Type", enum=['Group Membership', 'Admin User'])


class DeviceAdapterInstalledSoftware(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    vendor = Field(str, "Software Vendor")
    name = Field(str, "Software Name")
    version = Field(str, "Software Version")


class DeviceAdapterSoftwareCVE(SmartJsonClass):
    """ A definition for a CVE that is available for a software"""
    software_vendor = Field(str, "Software Vendor")
    software_name = Field(str, "Software Name")
    software_version = Field(str, "Software Version")
    cve_id = Field(str, "CVE ID")
    cve_description = Field(str, "CVE Description")
    cve_references = ListField(str, "CVE References")
    cve_severity = Field(str, "CVE Severity (Metric V3)")


class DeviceAdapter(SmartJsonClass):
    """ A definition for the json-scheme for a Device """

    name = Field(str, 'Asset Name')
    hostname = Field(str, 'Host Name')
    description = Field(str, 'Description')
    last_seen = Field(datetime.datetime, 'Last Seen')
    network_interfaces = ListField(DeviceAdapterNetworkInterface, 'Network Interfaces')
    os = Field(DeviceAdapterOS, 'OS')
    last_used_users = ListField(str, "Last Used User")
    installed_software = ListField(DeviceAdapterInstalledSoftware, "Installed Software")
    software_cves = ListField(DeviceAdapterSoftwareCVE, "Vulnerable Software")
    security_patches = ListField(DeviceAdapterSecurityPatch, "OS Installed Security Patches")
    available_security_patches = ListField(DeviceAdapterMsrcAvailablePatch, "OS Available Security Patches")
    connected_hardware = ListField(DeviceAdapterConnectedHardware, "Connected Hardware")
    id = Field(str, 'ID')
    part_of_domain = Field(bool, "Part Of Domain")
    domain = Field(str, "Domain")  # Only domain, e.g. "TestDomain.Test", or the computer name (local user)
    users = ListField(DeviceAdapterUser, "Users")
    local_admins = ListField(DeviceAdapterLocalAdmin, "Local Admins")
    pretty_id = Field(str, 'Axonius Name')
    device_manufacturer = Field(str, "Device Manufacturer")
    device_model = Field(str, "Device Model")
    device_model_family = Field(str, "Device Model Family")
    device_serial = Field(str, "Device Manufacturer Serial")
    pc_type = Field(str, "PC Type", enum=["Unspecified", "Desktop", "Laptop or Tablet", "Workstation",
                                          "Enterprise Server", "SOHO Server", "Appliance PC", "Performance Server",
                                          "Maximum"])
    number_of_processes = Field(int, "Number Of Processes")
    hard_drives = ListField(DeviceAdapterHD, "Hard Drives")
    cpus = ListField(DeviceAdapterCPU, "CPUs")
    boot_time = Field(datetime.datetime, 'Boot Time')
    time_zone = Field(str, 'Time Zone')
    bios_version = Field(str, "Bios Version")
    bios_serial = Field(str, "Bios Serial")
    total_physical_memory = Field(float, "Total RAM (GB)")
    free_physical_memory = Field(float, "Free RAM (GB)")
    physical_memory_percentage = Field(float, "RAM Usage (%)")
    total_number_of_physical_processors = Field(int, "Total Physical Processors")
    total_number_of_cores = Field(int, "Total Cores")
    batteries = ListField(DeviceAdapterBattery, "Battery")
    current_logged_user = Field(str, "Currently Logged User")
    device_disabled = Field(bool, "Device Disabled")
    power_state = Field(DeviceRunningState, "Power State")
    device_managed_by = Field(str, "Managed By")    # Who is the entity managing the device
    organizational_unit = ListField(str, "Organizational Unit")
    security_patch_level = Field(datetime.datetime, "Security Patch Level")
    scanner = Field(bool, 'Scanner')

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

    def add_nic(self, mac=None, ips=None, subnets=None, name=None):
        """
        Add a new network interface card to this device.
        :param mac: the mac
        :param ips: an IP list
        :param subnets: a Subnet list (format {ip}/{int/ipv4_subnet_mask})
        :param name: the interface name
        """
        nic = DeviceAdapterNetworkInterface()
        if mac is not None:
            if normalize_mac(mac) != '000000000000':
                try:
                    nic.mac = mac
                    nic.manufacturer = get_manufacturer_from_mac(mac)
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
        if subnets is not None:
            try:
                subnets_iter = iter(subnets)
            except TypeError:
                if logger is None:
                    raise
                logger.exception(f'Invalid subnets: {repr(subnets)}')
            else:
                for subnet in subnets_iter:
                    try:
                        subnet = format_subnet(subnet)  # formatting here just to make sure we don't add duplicates...
                        if subnet not in nic.subnets:
                            nic.subnets.append(subnet)
                    except (ValueError, TypeError):
                        if logger is None:
                            raise
                        logger.exception(f'Invalid subnet: {repr(subnet)}')
        if name is not None:
            try:
                nic.name = name
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid name : {repr(name)}')

        self.network_interfaces.append(nic)

    def figure_os(self, os_string):
        os_dict = figure_out_os(os_string)
        if os_dict is None:
            return
        self.os = DeviceAdapterOS(**os_dict)

    def add_battery(self, **kwargs):
        self.batteries.append(DeviceAdapterBattery(**kwargs))

    def add_local_admin(self, **kwargs):
        self.local_admins.append(DeviceAdapterLocalAdmin(**kwargs))

    def add_hd(self, **kwargs):
        self.hard_drives.append(DeviceAdapterHD(**kwargs))

    def add_cpu(self, **kwargs):
        self.cpus.append(DeviceAdapterCPU(**kwargs))

    def add_users(self, **kwargs):
        self.users.append(DeviceAdapterUser(**kwargs))

    def add_security_patch(self, **kwargs):
        self.security_patches.append(DeviceAdapterSecurityPatch(**kwargs))

    def add_available_security_patch(self, **kwargs):
        self.available_security_patches.append(DeviceAdapterMsrcAvailablePatch(**kwargs))

    def add_connected_hardware(self, **kwargs):
        self.connected_hardware.append(DeviceAdapterConnectedHardware(**kwargs))

    def add_installed_software(self, **kwargs):
        self.installed_software.append(DeviceAdapterInstalledSoftware(**kwargs))

    def add_vulnerable_software(self, **kwargs):
        self.software_cves.append(DeviceAdapterSoftwareCVE(**kwargs))


NETWORK_INTERFACES_FIELD = DeviceAdapter.network_interfaces.name
LAST_SEEN_FIELD = DeviceAdapter.last_seen.name
OS_FIELD = DeviceAdapter.os.name

MAC_FIELD = DeviceAdapterNetworkInterface.mac.name
IPS_FIELD = DeviceAdapterNetworkInterface.ips.name
