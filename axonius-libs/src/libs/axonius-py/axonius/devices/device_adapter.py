import datetime
import logging
import typing
import copy
from enum import Enum, auto

from axonius.blacklists import ALL_BLACKLIST
from axonius.clients.cisco.port_security import PortSecurityInterface
from axonius.fields import Field, JsonArrayFormat, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.mongo_escaping import escape_dict, unescape_dict
from axonius.utils.parsing import (
    figure_out_os,
    format_ip,
    format_ip_raw,
    format_mac,
    format_subnet,
    get_manufacturer_from_mac,
    normalize_mac,
)

logger = logging.getLogger(f'axonius.{__name__}')


"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class AdapterProperty(Enum):
    """
    Possible properties of the adapter
    """

    # pylint: disable=no-self-argument
    def _generate_next_value_(name, *args):
        return name

    # Naming scheme: Underscore is replaced with space for the facade, so "Antivirus_System" will show
    # as "Antivirus System" (see above _generate_next_value_)
    # Otherwise - provide a name: `AVSystem = "Antivirus System"`
    # TODO: Make the GUI actually support this
    Agent = auto()
    Endpoint_Protection_Platform = auto()
    Network = auto()
    Firewall = auto()
    Manager = auto()
    Vulnerability_Assessment = auto()
    Assets = auto()
    UserManagement = auto()
    Cloud_Provider = auto()
    Virtualization = auto()
    MDM = auto()


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
    Rebooting = auto()
    StartingUp = auto()
    Normal = auto()
    """
    State is unknown
    """
    Unknown = auto()
    """
    Error has occurred
    """
    Error = auto()
    """
    VM in migration process
    """
    Migrating = auto()


class DeviceAdapterOS(SmartJsonClass):
    """ A definition for the json-scheme for an OS (of a device) """

    type = Field(
        str, 'Type', enum=['Windows', 'Linux', 'OS X', 'iOS', 'AirOS',
                           'Android', 'FreeBSD', 'VMWare', 'Cisco', 'Mikrotik', 'VxWorks',
                           'F5 Networks Big-IP']
    )
    distribution = Field(str, 'Distribution')
    bitness = Field(int, 'Bitness', enum=[32, 64])
    sp = Field(str, 'Service Pack')
    install_date = Field(datetime.datetime, "Install Date")
    kernel_version = Field(str, 'Kernel Version')
    codename = Field(str, 'Code name')  # for example 'xenial'

    major = Field(int, 'Major')
    minor = Field(int, 'Minor')
    build = Field(str, 'Build')  # aka patch level


class DeviceAdapterVlan(SmartJsonClass):
    """ A definition for the json-scheme for a vlan """

    name = Field(str, 'Vlan Name')
    tagid = Field(int, 'Tag ID')
    tagness = Field(str, 'Vlan Tagness', enum=['Tagged', 'Untagged'])


class DeviceAdapterNetworkInterface(SmartJsonClass):
    """ A definition for the json-scheme for a network interface """

    name = Field(str, 'Iface Name')
    mac = Field(str, 'Mac', converter=format_mac)
    manufacturer = Field(str, 'Manufacturer')
    ips = ListField(str, 'IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    subnets = ListField(
        str,
        'Subnets',
        converter=format_subnet,
        json_format=JsonStringFormat.subnet,
        description='A list of subnets in ip format, that correspond the IPs',
    )
    ips_raw = ListField(
        str, description='Number representation of the IP, useful for filtering by range', converter=format_ip_raw
    )

    vlan_list = ListField(DeviceAdapterVlan, 'Vlans', description='A list of vlans in this interface')

    # Operational status enum from Cisco reference, which is industry standard.
    operational_status = Field(
        str, "Operational Status", enum=["Up", "Down", "Testing", "Unknown", "Dormant", "Nonpresent", "LowerLayerDown"]
    )
    admin_status = Field(str, "Admin Status", enum=["Up", "Down", "Testing"])

    speed = Field(str, "Interface Speed", description="Interface max speed per Second")
    port_type = Field(str, "Port Type", enum=["Access", "Trunk"])
    mtu = Field(str, "MTU", description="Interface Maximum transmission unit")
    gateway = Field(str, 'Gateway')
    port = Field(str, 'Port')


class ConnectionType(Enum):
    Direct = auto()
    Indirect = auto()


class DeviceAdapterNeighbor(SmartJsonClass):
    """ A definition for the json-scheme for an connected device """

    remote_name = Field(str, 'Remote Device Name')
    local_ifaces = ListField(DeviceAdapterNetworkInterface, 'Local Interface')
    remote_ifaces = ListField(DeviceAdapterNetworkInterface, 'Remote Device Iface')
    connection_type = Field(str, 'Connection Type', enum=ConnectionType)


class DeviceAdapterRelatedIps(DeviceAdapterNetworkInterface):
    """ A definition for the json-scheme for a related ips """

    pass


class DeviceAdapterHD(SmartJsonClass):
    """ A definition for hard drives on that device. On windows, that would be a drive.
    On linux and mac, we need to think what it is (not sure its mounts...) """

    path = Field(str, "Path")
    device = Field(str, "Device Name")
    file_system = Field(str, "Filesystem")
    total_size = Field(float, "Size (GB)")
    free_size = Field(float, "Free Size (GB)")
    is_encrypted = Field(bool, "Encrypted")
    description = Field(str, 'Description')


class DeviceAdapterCPU(SmartJsonClass):
    """ A definition for cpu's """

    name = Field(str, "Description")
    manufacturer = Field(str, "Manufacturer")
    bitness = Field(int, "Bitness", enum=[32, 64])
    family = Field(str, "Family")
    cores = Field(int, "Cores")
    cores_thread = Field(int, 'Threads in core')
    load_percentage = Field(int, "Load Percentage")
    architecture = Field(str, "Architecture", enum=["x86", "x64", "MIPS", "Alpha", "PowerPC", "ARM", "ia64"])
    ghz = Field(float, "Clockspeed (GHZ)")


class DeviceAdapterBattery(SmartJsonClass):
    """ A definition for a battery"""

    percentage = Field(int, "Percentage")
    status = Field(
        str,
        "Status",
        enum=[
            "Not Charging",
            "Connected to AC",
            "Fully Charged",
            "Low",
            "Critical",
            "Charging",
            "Charging and High",
            "Charging and Low",
            "Charging and Critical",
            "Undefined",
            "Partially Charged",
        ],
    )
    manufacturer = Field(str, "Manufacturer")
    model = Field(str, "Model")
    capacity = Field(str, "Capacity (mWh)")


class DeviceAdapterUser(SmartJsonClass):
    """ A definition for users known by this device"""

    user_sid = Field(str, "SID")
    # This will be treated as an ID in the users screen. should be username@domain. If there is no domain, domain
    # should be the hostname if the computer.
    username = Field(str, "Username")
    last_use_date = Field(datetime.datetime, 'Last Use Time')
    is_local = Field(bool, "Is Local")
    is_disabled = Field(bool, "Is Disabled")
    is_admin = Field(bool, "Is Admin")
    user_department = Field(str, "Department")
    password_max_age = Field(int, "Password Max Age")
    interpreter = Field(str, "Interpreter")

    # Hidden data for internal usage
    should_create_if_not_exists = Field(bool)  # If true, will create this user in the 'users' screen.
    creation_source_plugin_type = Field(str)
    creation_source_plugin_name = Field(str)
    creation_source_plugin_unique_name = Field(str)


class DeviceAdapterConnectedHardware(SmartJsonClass):
    """ A definition for connected devices of this device"""

    name = Field(str, "Name")
    manufacturer = Field(str, "Manufacturer")
    hw_id = Field(str, "ID")


class DeviceAdapterSecurityPatch(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    security_patch_id = Field(str, "Security Patch Name")
    installed_on = Field(datetime.datetime)
    patch_description = Field(str, 'Patch Description')
    classification = Field(str, 'Classification')
    state = Field(str, 'State')
    severity = Field(str, 'Severity')


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

    name = Field(str, "Software Name")
    version = Field(str, "Software Version")
    architecture = Field(
        str, "Software Architecture", enum=["x86", "x64", "MIPS", "Alpha", "PowerPC", "ARM", "ia64", "all"]
    )
    description = Field(str, "Software Description")
    vendor = Field(str, "Software Vendor")
    # This is not the same as Vendor in many cases. This is why I added it. OS
    publisher = Field(str, 'Software Publisher')
    cve_count = Field(str, 'CVE Count')
    sw_license = Field(str, 'License')
    path = Field(str, 'Software Path')


class DeviceAdapterAutorunData(SmartJsonClass):
    autorun_location = Field(str, 'Autorun Location')
    autorun_caption = Field(str, 'Autorun Caption')
    autorun_command = Field(str, 'Autorun Command')


class DeviceAdapterSoftwareCVE(SmartJsonClass):
    """ A definition for a CVE that is available for a software"""

    software_vendor = Field(str, "Software Vendor")
    software_name = Field(str, "Software Name")
    software_version = Field(str, "Software Version")
    cve_id = Field(str, "CVE ID")
    cve_description = Field(str, "CVE Description")
    cve_references = ListField(str, "CVE References")
    cve_severity = Field(str, "CVE Severity (Metric V3)")


class ShareData(SmartJsonClass):
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    path = Field(str, 'Path')


class DeviceTagKeyValue(SmartJsonClass):
    """ A Definition for a key-value tag """

    tag_key = Field(str, "Tag Key")
    tag_value = Field(str, "Tag Value")


class ShodanVuln(SmartJsonClass):
    vuln_name = Field(str, 'Vulnerability Name')
    cvss = Field(float, 'CVSS')
    summary = Field(str, 'Summary')


class ShodanData(SmartJsonClass):
    city = Field(str, 'City')
    region_code = Field(str, 'Region Code')
    country_name = Field(str, 'Country Name')
    org = Field(str, 'Organization')
    os = Field(str, 'OS')
    isp = Field(str, 'ISP')
    ports = ListField(int, 'Ports')
    vulns = ListField(ShodanVuln, 'Vulnerabilities')
    cpe = ListField(str, 'Cpe')
    http_location = Field(str, 'HTTP Location')
    http_server = Field(str, 'HTTP Server')
    http_site_map = Field(str, 'HTTP Site Map')
    http_security_text_hash = Field(str, 'HTTP Security Text')


class DeviceSwapFile(SmartJsonClass):
    """ A Definition for a key-value tag """

    name = Field(str, 'Name')
    size_in_gb = Field(int, 'Size (GB)')


class ProcessData(SmartJsonClass):
    name = Field(str, 'Name')


class RegistryInfomation(SmartJsonClass):
    reg_key = Field(str, 'Registry Key')
    value_name = Field(str, 'Value Name')
    value_data = Field(str, 'Value Data')
    last_changed = Field(datetime.datetime, 'Last Changed')


class ServiceData(SmartJsonClass):
    name = Field(str, 'Name')
    display_name = Field(str, 'Display Name')
    status = Field(str, 'Status')


class TenableVulnerability(SmartJsonClass):
    plugin = Field(str, 'plugin')
    severity = Field(str, 'severity')


class TenableSource(SmartJsonClass):
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    source = Field(str, 'Source')


class DeviceAdapter(SmartJsonClass):
    """ A definition for the json-scheme for a Device """
    name = Field(str, 'Asset Name')
    hostname = Field(str, 'Host Name')
    description = Field(str, 'Description')
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    fetch_time = Field(datetime.datetime, 'Fetch Time')
    public_ips = ListField(str, 'Public IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    public_ips_raw = ListField(
        str,
        description='Number representation of the Public IP, useful for filtering by range',
        converter=format_ip_raw,
    )
    network_interfaces = ListField(
        DeviceAdapterNetworkInterface, 'Network Interfaces', json_format=JsonArrayFormat.table
    )
    os = Field(DeviceAdapterOS, 'OS')
    last_used_users = ListField(str, "Last Used Users")
    last_used_users_departments_association = ListField(str, 'Last Used Users Departments')
    installed_software = ListField(
        DeviceAdapterInstalledSoftware, "Installed Software", json_format=JsonArrayFormat.table
    )
    autoruns_data = ListField(DeviceAdapterAutorunData, 'Autoruns Data', json_format=JsonArrayFormat.table)
    software_cves = ListField(DeviceAdapterSoftwareCVE, "Vulnerable Software", json_format=JsonArrayFormat.table)
    security_patches = ListField(
        DeviceAdapterSecurityPatch, "OS Security Patches", json_format=JsonArrayFormat.table
    )
    available_security_patches = ListField(
        DeviceAdapterMsrcAvailablePatch, "OS Available Security Patches", json_format=JsonArrayFormat.table
    )
    connected_hardware = ListField(
        DeviceAdapterConnectedHardware, "Connected Hardware", json_format=JsonArrayFormat.table
    )

    connected_devices = ListField(DeviceAdapterNeighbor, "Connected Devices", json_format=JsonArrayFormat.table)
    direct_connected_devices = ListField(
        DeviceAdapterNeighbor, "Direct Connected Devices", json_format=JsonArrayFormat.table)

    id = Field(str, 'ID')
    part_of_domain = Field(bool, "Part Of Domain")
    domain = Field(str, "Domain")  # Only domain, e.g. "TestDomain.Test", or the computer name (local user)
    users = ListField(DeviceAdapterUser, "Users", json_format=JsonArrayFormat.table)
    local_admins = ListField(DeviceAdapterLocalAdmin, "Local Admins", json_format=JsonArrayFormat.table)
    pretty_id = Field(str, 'Axonius Name')

    related_ips = Field(DeviceAdapterRelatedIps, "Related Ips")
    pc_type = Field(
        str,
        "PC Type",
        enum=[
            "Unspecified",
            "Desktop",
            "Laptop or Tablet",
            "Workstation",
            "Enterprise Server",
            "SOHO Server",
            "Appliance PC",
            "Performance Server",
            "Maximum",
            "Mobile",
        ],
    )
    physical_location = Field(str, 'Physical Location')
    number_of_processes = Field(int, "Number Of Processes")
    hard_drives = ListField(DeviceAdapterHD, "Hard Drives", json_format=JsonArrayFormat.table)
    cpus = ListField(DeviceAdapterCPU, "CPUs")
    time_zone = Field(str, 'Time Zone')
    boot_time = Field(datetime.datetime, 'Boot Time')
    uptime = Field(int, 'Uptime (Days)')

    # hardware related
    device_manufacturer = Field(str, "Device Manufacturer")
    device_model = Field(str, "Device Model")
    device_model_family = Field(str, "Device Model Family")
    device_serial = Field(str, "Device Manufacturer Serial")

    bios_version = Field(str, "Bios Version")
    bios_serial = Field(str, "Bios Serial")

    motherboard_manufacturer = Field(str, "Motherboard Manufacturer")
    motherboard_serial = Field(str, "Motherboard serial")
    motherboard_model = Field(str, "Motherboard Model")
    motherboard_version = Field(str, "Motherboard Version")

    total_physical_memory = Field(float, "Total RAM (GB)")
    free_physical_memory = Field(float, "Free RAM (GB)")
    physical_memory_percentage = Field(float, "RAM Usage (%)")
    swap_files = ListField(DeviceSwapFile, 'Swap Files')
    swap_total = Field(float, 'Total Swap GB')
    swap_cached = Field(float, 'Cached Swap GB')
    swap_free = Field(float, 'Free Swap GB')
    total_number_of_physical_processors = Field(int, "Total Physical Processors")
    total_number_of_cores = Field(int, "Total Cores")
    batteries = ListField(DeviceAdapterBattery, "Battery")
    current_logged_user = Field(str, "Currently Logged User")
    device_disabled = Field(bool, "Device Disabled")
    power_state = Field(DeviceRunningState, "Power State")
    device_managed_by = Field(str, "Managed By")  # Who is the entity managing the device
    organizational_unit = ListField(str, "Organizational Unit")
    security_patch_level = Field(datetime.datetime, "Security Patch Level")
    scanner = Field(bool, 'Scanner')
    tags = ListField(DeviceTagKeyValue, "Tags")
    cloud_provider = Field(str, "Cloud Provider")
    cloud_id = Field(str, "Cloud ID")
    shodan_data = Field(ShodanData, 'Shodan Data')
    processes = ListField(ProcessData, 'Running Processes', json_format=JsonArrayFormat.table)
    services = ListField(ServiceData, 'Services', json_format=JsonArrayFormat.table)
    shares = ListField(ShareData, 'Shares', json_format=JsonArrayFormat.table)
    adapter_properties = ListField(str, 'Adapter Properties', enum=AdapterProperty)
    port_security = ListField(PortSecurityInterface, 'Port Security', json_format=JsonArrayFormat.table)
    dns_servers = ListField(str, 'DNS Servers')
    dhcp_servers = ListField(str, 'DHCP Servers')
    uuid = Field(str, 'UUID')
    plugin_and_severities = ListField(TenableVulnerability, 'Plugins and Severities',
                                      json_format=JsonArrayFormat.table)
    tenable_sources = ListField(TenableSource, 'Tenable Source',
                                json_format=JsonArrayFormat.table)
    registry_information = ListField(
        RegistryInfomation, 'Registry Information', json_format=JsonArrayFormat.table
    )
    required = ['name', 'hostname', 'os', 'network_interfaces']

    def generate_direct_connected_devices(self):
        try:
            for connected_device in self.connected_devices:
                if connected_device.connection_type == ConnectionType.Direct.name:
                    self.direct_connected_devices.append(connected_device)
        except Exception:
            logger.exception('Failed to generate direct connected devices')

    def __init__(self, adapter_fields: typing.MutableSet[str], adapter_raw_fields: typing.MutableSet[str]):
        """ The adapter_fields and adapter_raw_fields will be auto-populated when new fields are set. """
        super().__init__()
        # do not pass kwargs to constructor before setting up self._adapter_fields
        # because its supposed to populate the names of the fields into it - see _define_new_name override here
        self._adapter_fields = adapter_fields
        self._adapter_raw_fields = adapter_raw_fields
        self._raw_data = {}  # will hold any extra raw fields that are associated with this device.

    def add_public_ip(self, ip):
        try:
            self.public_ips.append(ip)
            self.public_ips_raw.append(ip)
        except Exception:
            logger.exception(f'Bad public ip {ip}')

    def _define_new_name(self, name: str):
        if name.startswith('raw.'):
            target_field_list = self._adapter_raw_fields
        else:
            target_field_list = self._adapter_fields
        target_field_list.add(name)

    def declare_new_field(self, *args, **kwargs):
        assert self.__class__ != DeviceAdapter, (
            'Can not change DeviceAdapter, its generic! '
            'see test_smart_json_class.py::test_schema_change_for_special_classes'
        )
        super().declare_new_field(*args, **kwargs)

    def set_boot_time(self, *, boot_time: datetime.datetime = None, uptime: datetime.timedelta = None):
        """ set boot time and uptime using one of them """
        try:
            if boot_time is None and uptime is None:
                raise RuntimeError('Missing required parameters')

            if not any([boot_time, uptime]):
                logger.debug(f'empty time {boot_time} {uptime}')
                return

            if boot_time:
                self.boot_time = boot_time
                try:
                    current_time = parse_date(datetime.datetime.now())
                    self.uptime = (current_time - boot_time).days
                except Exception:
                    logger.debug(f'Problem getting uptime from boot time')
                return

            if uptime:
                self.uptime = uptime.days
                current_time = parse_date(datetime.datetime.now())
                self.boot_time = current_time - uptime
                return

        except Exception:
            logger.exception(f'Failed to set boot time {boot_time} {uptime}')

    def set_raw(self, raw_data: dict):
        """ Sets the raw fields associated with this device and also updates adapter_raw_fields.
            Use only this function because it also fixes '.' in the keys such that it will work on MongoDB.
        """
        assert isinstance(raw_data, dict)
        raw_data = escape_dict(raw_data)
        self._raw_data = raw_data
        self._dict['raw'] = self._raw_data
        self._extend_names('raw', raw_data)

    def get_raw(self):
        return unescape_dict(self._raw_data)

    def set_related_ips(self, ips):
        related_ips = DeviceAdapterRelatedIps()
        related_ips = self.__add_ips_and_subnets(related_ips, ips, None)
        self.related_ips = related_ips

    def __add_ips_and_subnets(self, obj, ips, subnets):
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
                        if ip and isinstance(ip, str) and ip != '0.0.0.0':
                            obj.ips.append(ip)
                            obj.ips_raw.append(ip)
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
                        if subnet not in obj.subnets:
                            obj.subnets.append(subnet)
                    except (ValueError, TypeError):
                        if logger is None:
                            raise
                        logger.exception(f'Invalid subnet: {repr(subnet)}')
        return obj

    def add_ips_and_macs(self, macs=None, ips=None):
        """
            add a list of macs and ips that doesn't relates to the same nic
        """
        if macs is None:
            macs = []

        if ips is None:
            ips = []

        # Convert single string to list
        if macs and isinstance(macs, (str, bytes)):
            macs = [macs]

        # Validate list, throw other
        try:
            macs = list(macs)
        except TypeError as te:
            logger.error(f'failed to handle mac {macs}')
            macs = []

        if ips and isinstance(ips, (str, bytes)):
            ips = [ips]

        # Validate list, throw other
        try:
            ips = list(ips)
        except TypeError as te:
            logger.error(f'failed to handle ips {ips}')
            ips = []

        # If only one mac assume the ips are related and just add nic
        if macs and len(macs) == 1:
            try:
                self.add_nic(macs[0], ips)
            except Exception:
                logger.exception(f'Failed to add macs and ips {macs} {ips}')
            return

        # multiple mac, assume different interfaces
        for mac in macs:
            try:
                self.add_nic(mac=mac)
            except Exception:
                logger.exception(f'Failed to add mac {mac}')

        for ip in ips:
            try:
                self.add_nic(ips=[ip])
            except Exception:
                logger.exception(f'Failed to add ip {ip}')

    def add_nic(
        self,
        mac=None,
        ips=None,
        subnets=None,
        name=None,
        speed=None,
        mtu=None,
        operational_status=None,
        admin_status=None,
        vlans=None,
        port_type=None,
        gateway=None,
        port=None,
    ):
        """
        Add a new network interface card to this device.
        :param mac: the mac
        :param ips: an IP list
        :param subnets: a Subnet list (format {ip}/{int/ipv4_subnet_mask})
        :param name: the interface name
        """
        nic = DeviceAdapterNetworkInterface()
        if mac is not None:
            mac = str(mac)
            if normalize_mac(mac) != '000000000000' and normalize_mac(mac) not in ALL_BLACKLIST:
                try:
                    nic.mac = mac
                    nic.manufacturer = get_manufacturer_from_mac(mac)
                except (ValueError, TypeError):
                    if logger is None:
                        raise
                    logger.info(f'Invalid mac: {repr(mac)}')
        nic = self.__add_ips_and_subnets(nic, ips, subnets)
        if name is not None:
            try:
                nic.name = name
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid name: {repr(name)}')

        if port is not None:
            try:
                nic.port = port
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid port: {repr(port)}')
        if mtu is not None:
            try:
                nic.mtu = int(mtu)
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid mtu: {repr(mtu)}')

        if speed is not None:
            try:
                nic.speed = speed
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid speed: {repr(speed)}')

        if operational_status is not None:
            try:
                nic.operational_status = operational_status
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid operational_status: {repr(operational_status)}')

        if admin_status is not None:
            try:
                nic.admin_status = admin_status
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid admin_status: {repr(admin_status)}')

        if port_type is not None:
            try:
                nic.port_type = port_type
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.exception(f'Invalid port_type: {repr(port_type)}')

        if vlans is not None:
            try:
                nic.vlan_list = vlans
            except Exception:
                if logger is None:
                    raise
                logger.exception(f'Invalid vlans: {repr(vlans)}')

        if gateway is not None:
            try:
                nic.gateway = gateway
            except Exception:
                if logger is None:
                    raise
                logger.exception(f'Invalid gateway: {repr(vlans)}')

        self.network_interfaces.append(nic)

    def figure_os(self, os_string):

        os_dict = figure_out_os(str(os_string))
        if os_dict is None:
            return

        try:
            old_dict = copy.copy(self.os.to_dict())
            for key, value in os_dict.items():
                if value:
                    old_dict[key] = value
            os_dict = old_dict
        except Exception:
            pass
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

    def add_autorun_data(self, **kwargs):
        self.autoruns_data.append(DeviceAdapterAutorunData(**kwargs))

    def add_installed_software(self, **kwargs):
        arch_translate_dict = {
            'amd64': 'x64',
            'x86_64': 'x64',
            '64-bit': 'x64',
            '64 bit': 'x64',
            'Win64': 'x64',
            'i386': 'x86',
            '32-bit': 'x86',
            'noarch': 'all',
            'none': 'all',
            '(none)': 'all',
        }

        if 'architecture' in kwargs and kwargs['architecture'] in arch_translate_dict.keys():
            kwargs['architecture'] = arch_translate_dict[kwargs['architecture']]

        self.installed_software.append(DeviceAdapterInstalledSoftware(**kwargs))

    def add_vulnerable_software(self, **kwargs):
        self.software_cves.append(DeviceAdapterSoftwareCVE(**kwargs))

    def add_key_value_tag(self, key, value):
        self.tags.append(DeviceTagKeyValue(tag_key=key, tag_value=value))

    def set_shodan_data(self, **kwargs):
        self.shodan_data = ShodanData(**kwargs)

    def add_swap_file(self, name, size_in_gb):
        self.swap_files.append(DeviceSwapFile(name=name, size_in_gb=size_in_gb))

    def add_share(self, **kwargs):
        self.shares.append(ShareData(**kwargs))

    def add_process(self, **kwargs):
        self.processes.append(ProcessData(**kwargs))

    def add_service(self, **kwargs):
        self.services.append(ServiceData(**kwargs))


NETWORK_INTERFACES_FIELD = DeviceAdapter.network_interfaces.name
LAST_SEEN_FIELD = DeviceAdapter.last_seen.name
OS_FIELD = DeviceAdapter.os.name

MAC_FIELD = DeviceAdapterNetworkInterface.mac.name
IPS_FIELD = DeviceAdapterNetworkInterface.ips.name
