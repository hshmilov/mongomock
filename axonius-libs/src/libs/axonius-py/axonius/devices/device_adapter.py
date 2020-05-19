import datetime
import ipaddress
import logging
import typing
import copy
from enum import Enum, auto
from collections import namedtuple

from axonius.blacklists import ALL_BLACKLIST
from axonius.clients.cisco.port_security import PortSecurityInterface
from axonius.clients.cisco.port_access import PortAccessEntity
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
    replace_large_ints,
    parse_versions_raw
)

MAX_SIZE_OF_MONGO_DOCUMENT = (1024**2) * 10

AGENTS = namedtuple('Agents', (
    'alertlogic', 'bigfix', 'carbonblack_defense', 'carbonblack_protection', 'carbonblack_response', 'cisco_amp',
    'cisco_firepower_management_center', 'cisco_umbrella', 'cloudpassage', 'code42', 'counter_act', 'crowd_strike',
    'cylance', 'datadog', 'desktop_central', 'dropbox', 'druva', 'endgame', 'ensilo', 'epo', 'fireeye_hx',
    'forcepoint_csv', 'imperva_dam', 'jumpcloud', 'kaseya', 'lansweeper', 'minerva', 'mobi_control', 'mobileiron',
    'observeit', 'opswat', 'paloalto_cortex', 'qualys_scans', 'quest_kace', 'redcloak', 'sccm',
    'secdo', 'sentinelone', 'signalsciences', 'traps', 'eclypsium', 'malwarebytes_cloud',
    'sophos', 'symantec', 'symantec_cloud_workload', 'symantec_ee', 'symantec_12', 'tanium', 'tenable_io', 'tripwire',
    'truefort', 'guardicore', 'deep_security', 'illusive', 'bitdefender', 'avamar',
    'twistlock', 'webroot', 'aqua', 'symantec_dlp', 'bitlocker', 'wazuh', 'wsus', 'microfocus_sa', 'contrast',
))

AGENT_NAMES = AGENTS(
    alertlogic='Alert Logic Agent', bigfix='IBM BigFix Agent', carbonblack_defense='CarbonBlack Defense Sensor',
    carbonblack_protection='CarbonBlack Protection Sensor', carbonblack_response='CarbonBlack Response Sensor',
    cisco_amp='Cisco AMP Connector', cisco_firepower_management_center='Cisco FMC Agent',
    bitlocker='Bitlocker Agent', traps='Traps Agent', avamar='Avamar Client',
    malwarebytes_cloud='Malwarebytes Agent',
    cisco_umbrella='Cisco Umbrella Agent', cloudpassage='CloudPassage Daemon', code42='Code42 Agent',
    counter_act='CounterACT Agent', crowd_strike='CrowdStrike Agent', cylance='Cylance Agent', datadog='Datadog Agent',
    desktop_central='Desktop Central Agent', dropbox='Dropbox Client', druva='Druva Client', endgame='Endgame Sensor',
    ensilo='enSilo Agent', epo='McAfee EPO Agent', fireeye_hx='FireEye HX Agent', forcepoint_csv='Forcepoint Client',
    imperva_dam='Imperva DAM Agent', jumpcloud='JumpCloud Agent', kaseya='Kaseya Agent', lansweeper='Lansweeper Agent',
    minerva='Minerva Labs Agent', mobi_control='MobiControl Agent', mobileiron='MobileIron Client',
    observeit='ObserveIT Client', opswat='OPSWAT Agent', paloalto_cortex='Palo Alto Networks Cortex Agent',
    sccm='Microsoft SCCM Client', eclypsium='Eclypsium Agent',
    qualys_scans='Qualys Agent', quest_kace='Quest Client', redcloak='Redcloak Agent', secdo='Secdo Agent',
    sentinelone='SentinelOne Agent', signalsciences='Signalsciences Agent',
    sophos='Sophos Agent', symantec='Symantec SEP 14 Agent', illusive='Illusive Agent',
    symantec_cloud_workload='Symantec Cloud Agent', symantec_ee='Symantec Endpoint Encryption Agent',
    tanium='Tanium Agent', tenable_io='Tenable io Agent', bitdefender='Bitdefender Gravity Zone Agent',
    tripwire='Tripwire Agent', truefort='TrueFort Agent', twistlock='Twistlock Agent',
    webroot='Webroot Agent', symantec_12='Symantec SEP 12 Agent', wazuh='Wazuh Agent',
    aqua='Aqua Enforcer', symantec_dlp='Symantec DLP Agent', guardicore='Guardicore Agent',
    deep_security='DeepSecurity Agent', wsus='WSUS Client', microfocus_sa='Microfocus Server Automation',
    contrast='Contrast Security Agent',
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
                           'Android', 'FreeBSD', 'VMWare', 'Cisco', 'Mikrotik', 'VxWorks', 'PanOS',
                           'F5 Networks Big-IP', 'Solaris', 'AIX', 'Printer', 'PlayStation', 'Check Point', "Arista",
                           'Netscaler']
    )
    distribution = Field(str, 'Distribution')
    is_windows_server = Field(bool, 'Is Windows Server')
    os_str = Field(str, 'Full OS String')
    bitness = Field(int, 'Bitness', enum=[32, 64])
    sp = Field(str, 'Service Pack')
    install_date = Field(datetime.datetime, "Install Date")
    kernel_version = Field(str, 'Kernel Version')
    codename = Field(str, 'Code name')  # for example 'xenial'
    major = Field(int, 'Major')
    minor = Field(int, 'Minor')
    build = Field(str, 'Build')  # aka patch level
    serial = Field(str, 'Serial')


class DeviceAdapterVlan(SmartJsonClass):
    """ A definition for the json-scheme for a vlan """

    name = Field(str, 'Vlan Name')
    tagid = Field(int, 'Tag ID')
    tagness = Field(str, 'Vlan Tagness', enum=['Tagged', 'Untagged'])


class DeviceAdapterNetworkInterface(SmartJsonClass):
    """ A definition for the json-scheme for a network interface """

    name = Field(str, 'Iface Name')
    mac = Field(str, 'MAC', converter=format_mac)
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
        str, description='Number representation of the IP, useful for filtering by range',
        converter=format_ip_raw,
        hidden=True
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
    serial_number = Field(str, 'Serial Number')


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

    # Note! this is not just an 'MSRC' available patch. Its for all OS's.
    # But i do not want to refactor the name right now.
    title = Field(str, "Title")
    security_bulletin_ids = ListField(str, "Security Bulletin ID's")
    kb_article_ids = ListField(str, "KB Article ID's")
    msrc_severity = Field(str, "MSRC Severity")
    patch_type = Field(str, "Type", enum=["Software", "Driver"])
    state = Field(str, 'State')
    severity = Field(str, 'Severity')
    categories = ListField(str, "Categories")
    publish_date = Field(datetime.datetime, "Publish Date")


class DeviceAdapterLocalAdmin(SmartJsonClass):
    """A definition for local admins list"""

    admin_name = Field(str, "Name of user or group")
    admin_type = Field(str, "Admin Type", enum=['Group Membership', 'Admin User'])


class DeviceAdapterInstalledSoftware(SmartJsonClass):
    """ A definition for installed security patch on this device"""

    name = Field(str, "Software Name")
    version = Field(str, "Software Version", json_format=JsonStringFormat.version)
    name_version = Field(str, 'Software Name and Version')
    architecture = Field(
        str, "Software Architecture", enum=["x86", "x64", "MIPS", "Alpha", "PowerPC", "ARM", "ia64", "all", 'i686']
    )
    description = Field(str, "Software Description")
    vendor = Field(str, "Software Vendor")
    # This is not the same as Vendor in many cases. This is why I added it. OS
    publisher = Field(str, 'Software Publisher')
    cve_count = Field(str, 'CVE Count')
    sw_license = Field(str, 'License')
    path = Field(str, 'Software Path')
    version_raw = Field(str, hidden=True)


class DeviceAdapterAutorunData(SmartJsonClass):
    autorun_location = Field(str, 'Autorun Location')
    autorun_caption = Field(str, 'Autorun Caption')
    autorun_command = Field(str, 'Autorun Command')


class DeviceAdapterSoftwareCVE(SmartJsonClass):
    """ A definition for a CVE that is available for a software"""

    cve_id = Field(str, "CVE ID")
    software_name = Field(str, "Software Name")
    software_version = Field(str, "Software Version", json_format=JsonStringFormat.version)
    software_vendor = Field(str, "Software Vendor")
    cvss_version = Field(str, "CVSS Version", enum=['v2.0', 'v3.0'])
    cvss = Field(float, "CVSS")
    cvss_str = Field(str, 'CVSS String')
    cve_severity = Field(str, "CVE Severity", enum=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    cve_description = Field(str, "CVE Description")
    cve_synopsis = Field(str, "CVE Synopsis")
    cve_references = ListField(str, "CVE References")
    version_raw = Field(str)


class DeviceAdapterSoftwareLibraryCVE(SmartJsonClass):
    """ A definition for a CVE that is available for a software's library"""
    cve_id = Field(str, "CVE ID")
    software_name = Field(str, "Software Name")
    software_version = Field(str, "Software Version", json_format=JsonStringFormat.version)
    software_vendor = Field(str, "Software Vendor")
    library_name = Field(str, "Library Name")
    library_version = Field(str, "Library Version", json_format=JsonStringFormat.version)
    library_version_raw = Field(str, hidden=True)
    cvss = Field(float, "CVSS")
    cve_severity = Field(str, "CVE Severity", enum=["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    cve_description = Field(str, "CVE Description")


class ShareData(SmartJsonClass):
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    path = Field(str, 'Path')
    status = Field(str, 'Status')


class DeviceTagKeyValue(SmartJsonClass):
    """ A Definition for a key-value tag """

    tag_key = Field(str, "Tag Key")
    tag_value = Field(str, "Tag Value")


class DeviceAdapterAgentVersion(SmartJsonClass):
    agent_name_dict = {'bigfix_adapter': 'IBM BigFix'}
    adapter_name = Field(str, 'Name', enum=list(AGENT_NAMES))
    agent_version = Field(str, 'Version', json_format=JsonStringFormat.version)
    agent_version_raw = Field(str)
    agent_status = Field(str, 'Status')


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


class DeviceOpenPort(SmartJsonClass):
    protocol = Field(str, 'Protocol', enum=['TCP', 'UDP'])
    port_id = Field(int, 'Port Number')
    service_name = Field(str, 'Service Name')


class DeviceOpenPortVulnerabilityAndFix(SmartJsonClass):
    """ A definition for a CVE that regarding an open port"""

    port_id = ListField(int, 'Port Number')
    cve_id = Field(str, 'CVE ID')
    cve_description = Field(str, 'CVE Description')
    cve_severity = Field(float, 'CVE Severity')
    wasc_id = Field(str, 'WASC ID')
    vuln_solution = Field(str, 'Vulnerability Solution')
    fix_title = Field(str, 'Fix Title')
    fix_diagnosis = Field(str, 'Fix Diagnosis')
    fix_consequence = Field(str, 'Fix Consequence')
    fix_solution = Field(str, 'Fix Solution')
    fix_url = Field(str, 'Fix Url')
    fix_updated_at = Field(datetime.datetime, 'Fix updated at')
    patch_publication_date = Field(datetime.datetime, 'Patch publication date')


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


# pylint: disable=too-many-instance-attributes
class NessusInstance(SmartJsonClass):
    version = Field(str, 'Version')
    plugin_feed_version = Field(str, 'Plugin Feed Version')
    scanner_edition_used = Field(str, 'Scanner Edition Used')
    scan_type = Field(str, 'Scan Type')
    scan_policy_used = Field(str, 'Scan Policy Used')
    scanner_ip = Field(str, 'Scanner IP')
    port_scanner = Field(str, 'Port Scanner(s)')
    port_range = Field(str, 'Port Range')
    thorough_tests = Field(bool, 'Thorough Tests')
    experimental_tests = Field(bool, 'Experimental Tests')
    paranoia_level = Field(int, 'Paranoia Level')
    report_verbosity = Field(int, 'Report Verbosity')
    safe_check = Field(bool, 'Safe Checks')
    patch_management_checks = Field(str, 'Patch Management Checks')
    cgi_scanning = Field(str, 'CGI Scanning')
    max_hosts = Field(int, 'Max Hosts')
    max_checks = Field(int, 'Max Checks')
    receive_timeout = Field(int, 'Receive Timeout')
    scan_start_date = Field(datetime.datetime, 'Scan Start Date')
    scan_duration = Field(int, 'Scan Duration (sec)',)
    credentialed_check = Field(str, 'Credentialed Check')


class TenableVulnerability(SmartJsonClass):
    plugin_id = Field(str, 'Plugin ID')
    output = Field(str, 'Output')
    plugin = Field(str, 'Plugin')
    severity = Field(str, 'Severity')
    cpe = Field(str, 'Cpe')
    cve = Field(str, 'CVE')
    cvss_base_score = Field(float, 'CVSS Base Score')
    exploit_available = Field(bool, 'Exploit Available')
    synopsis = Field(str, 'Synopsis')
    see_also = Field(str, 'See Also')
    nessus_instance = Field(NessusInstance, 'Nessus Scan')
    plugin_text = Field(str, 'Vulnerability Text')


class TenableSource(SmartJsonClass):
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    source = Field(str, 'Source')


class FirewallRule(SmartJsonClass):
    name = Field(str, 'Name')
    source = Field(str, 'Source')
    type = Field(str, 'Allow / Deny', enum=['Allow', 'Deny'])
    direction = Field(str, 'Direction', enum=['INGRESS', 'EGRESS'])
    target = Field(str, 'Target')   # Target. This could be ip rage / security group / service account / tag / ...
    protocol = Field(str, 'Protocol')
    from_port = Field(int, 'From port')
    to_port = Field(int, 'To port')


class ScriptInformation(SmartJsonClass):
    script_id = Field(str, 'Script Id')
    script_output = Field(str, 'Script Output')


class NmapPortInfo(SmartJsonClass):
    protocol = Field(str, 'Protocol')
    portid = Field(str, 'Port Id')
    state = Field(str, 'State')
    reason = Field(str, 'Reason')
    service_name = Field(str, 'Service Name')
    service_product = Field(str, 'Service Product')
    service_method = Field(str, 'Service Method')
    service_conf = Field(str, 'Service Configuration')
    service_extra_info = Field(str, 'Service Extra Info')
    cpe = Field(str, 'cpe')
    script_information = ListField(ScriptInformation, 'Script Information')


class PortScriptInformation(SmartJsonClass):
    script_id = Field(str, 'Script Id')
    script_output = Field(str, 'Script Output')
    protocol = Field(str, 'Protocol')
    portid = Field(str, 'Port Id')


QUALYS_SUB_CATEGORIES = ['Authenticated Discovery',
                         'Malware Associated',
                         'Unix Authenticated Discovery',
                         'Remote Discovery',
                         'Patch Available',
                         'PANOS Authenticated Discovery',
                         'MongoDB Authenticated Discovery',
                         'MARIADB Authenticated Discovery',
                         'Not exploitable due to configuration',
                         'Exploit Available',
                         'SNMP Authenticated Discovery',
                         'Non-running services',
                         'Windows Authenticated Discovery',
                         'VMware Authenticated Discovery',
                         'MySQL Authenticated Discovery',
                         'Oracle Authenticated Discovery',
                         'Remote DiscoveryAuthenticated Discovery',
                         'DB2 Authenticated Discovery']

QUALYS_CATEGORIES = ['Debian',
                     'HP-UX',
                     'Amazon Linux',
                     'Hardware',
                     'Fedora',
                     'RPC',
                     'Finger',
                     'SUSE',
                     'Database',
                     'Web server',
                     'VMware',
                     'Firewall',
                     'File Transfer Protocol',
                     'News Server',
                     'NFS',
                     'CGI',
                     'Solaris',
                     'Oracle VM Server',
                     'RedHat',
                     'Windows',
                     'Proxy',
                     'Web Application Firewall',
                     'Brute Force Attack',
                     'General remote services',
                     'Security Policy',
                     'DNS and BIND',
                     'Mail services',
                     'Ubuntu',
                     'Forensics',
                     'Web Application',
                     'SMB / NETBIOS',
                     'X-Window',
                     'OEL',
                     'Cisco',
                     'AIX',
                     'CentOS',
                     'Local',
                     'Office Application',
                     'Backdoors and trojan horses',
                     'Internet Explorer',
                     'E-Commerce',
                     'SNMP',
                     'Information gathering',
                     'TCP/IP']

QUALYS_VULN_TYPES = [
    'Potential Vulnerability',
    'Confirmed Vulnerability',
    'Information Gathered'
]


class QualysAgentVuln(SmartJsonClass):
    vuln_id = Field(str, 'Vuln ID')
    first_found = Field(datetime.datetime, 'First Found')
    last_found = Field(datetime.datetime, 'Last Found')
    qid = Field(str, 'QID')
    title = Field(str, 'Title')
    category = Field(str, 'Category', enum=QUALYS_CATEGORIES)
    sub_category = ListField(str, 'Sub Category', enum=QUALYS_SUB_CATEGORIES)
    severity = Field(int, 'Severity')
    vendor_reference = ListField(str, 'Vendor Reference')
    qualys_cve_id = ListField(str, 'CVE ID')
    cvss_base = Field(float, 'CVSS Base')
    cvss3_base = Field(float, 'CVSS3 Base')
    cvss_temporal_score = Field(float, 'CVSS Temporal Score')
    cvss3_temporal_score = Field(float, 'CVSS3 Temporal Score')
    cvss_access_vector = Field(float, 'CVSS Access Vector')
    bugtraq_id = ListField(str, 'Bugtraq ID')
    modified = Field(datetime.datetime, 'Modified')
    published = Field(datetime.datetime, 'Published')
    vuln_type = Field(str, 'Vulnerability Type', enum=QUALYS_VULN_TYPES)


class DeviceAdapter(SmartJsonClass):
    """ A definition for the json-scheme for a Device """
    name = Field(str, 'Asset Name')
    hostname = Field(str, 'Host Name')
    description = Field(str, 'Description')
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    fetch_time = Field(datetime.datetime, 'Fetch Time')
    first_fetch_time = Field(datetime.datetime, 'First Fetch Time')
    email = Field(str, 'Email Address')
    owner = Field(str, 'Owner')
    public_ips = ListField(str, 'Public IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    public_ips_raw = ListField(
        str,
        description='Number representation of the Public IP, useful for filtering by range',
        converter=format_ip_raw,
        hidden=True
    )
    open_ports = ListField(DeviceOpenPort, 'Open Ports', json_format=JsonArrayFormat.table)
    open_ports_vulns_and_fixes = ListField(DeviceOpenPortVulnerabilityAndFix,
                                           "Open Ports Vulnerablities And Fixes",
                                           json_format=JsonArrayFormat.table)
    ports_info = ListField(NmapPortInfo, 'Ports Information', json_format=JsonArrayFormat.table)
    scripts_info = ListField(PortScriptInformation, 'Scripts Information', json_format=JsonArrayFormat.table)
    network_interfaces = ListField(
        DeviceAdapterNetworkInterface, 'Network Interfaces', json_format=JsonArrayFormat.table
    )
    os = Field(DeviceAdapterOS, 'OS')
    os_guess = Field(DeviceAdapterOS, 'OS Guess')
    last_used_users = ListField(str, "Last Used Users")
    last_used_users_departments_association = ListField(str, 'Last Used Users Departments')
    last_used_users_ad_display_name_association = ListField(str, 'Last Used Users AD Display Name')
    last_used_users_mail_association = ListField(str, 'Last Used Users Email')
    last_used_users_division_association = ListField(str, 'Last Used Users Division')
    last_used_users_company_association = ListField(str, 'Last Used Users Company')
    last_used_users_organizational_unit_association = ListField(str, 'Last Used Users Organizational Unit')
    last_used_users_description_association = ListField(str, 'Last Used Users Description')
    installed_software = ListField(
        DeviceAdapterInstalledSoftware, "Installed Software", json_format=JsonArrayFormat.table
    )
    autoruns_data = ListField(DeviceAdapterAutorunData, 'Autoruns Data', json_format=JsonArrayFormat.table)
    software_cves = ListField(DeviceAdapterSoftwareCVE, "Vulnerable Software", json_format=JsonArrayFormat.table)
    security_patches = ListField(
        DeviceAdapterSecurityPatch, "OS Installed Security Patches", json_format=JsonArrayFormat.table
    )
    available_security_patches = ListField(
        DeviceAdapterMsrcAvailablePatch, "OS Available Security Patches", json_format=JsonArrayFormat.table
    )
    software_library_cves = ListField(DeviceAdapterSoftwareLibraryCVE, "Software Libraries with Vulnerablities",
                                      json_format=JsonArrayFormat.table)
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
    local_admins_users = ListField(str, 'Local Admins - Users')
    local_admins_domain_users = ListField(str, 'Local Admins - Domain Users')
    local_admins_local_users = ListField(str, 'Local Admins - Local Users')
    local_admins_groups = ListField(str, 'Local Admins - Groups')
    pretty_id = Field(str, 'Axonius Name')
    agent_versions = ListField(DeviceAdapterAgentVersion, 'Agent Versions', json_format=JsonArrayFormat.table)

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

    bios_manufacturer = Field(str, "Bios Manufacturer")
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
    tags = ListField(DeviceTagKeyValue, "Adapter Tags")
    cloud_provider = Field(str, "Cloud Provider")
    cloud_id = Field(str, "Cloud ID")
    shodan_data = Field(ShodanData, 'Shodan Data')
    processes = ListField(ProcessData, 'Running Processes', json_format=JsonArrayFormat.table)
    services = ListField(ServiceData, 'Services', json_format=JsonArrayFormat.table)
    shares = ListField(ShareData, 'Shares', json_format=JsonArrayFormat.table)
    virtual_host = Field(bool, 'Is Virtual Host')
    adapter_properties = ListField(str, 'Adapter Properties', enum=AdapterProperty)
    port_security = ListField(PortSecurityInterface, 'Port Security', json_format=JsonArrayFormat.table)
    port_access = ListField(PortAccessEntity, 'Port Access', json_format=JsonArrayFormat.table)
    dns_servers = ListField(str, 'DNS Servers')
    dhcp_servers = ListField(str, 'DHCP Servers')
    uuid = Field(str, 'UUID')
    plugin_and_severities = ListField(TenableVulnerability, 'Plugins Information',
                                      json_format=JsonArrayFormat.table)
    qualys_agent_vulns = ListField(QualysAgentVuln, 'Qualys Vulnerabilities', json_format=JsonArrayFormat.table)
    registry_information = ListField(
        RegistryInfomation, 'Registry Information', json_format=JsonArrayFormat.table
    )
    firewall_rules = ListField(FirewallRule, 'Firewall Rules', json_format=JsonArrayFormat.table)
    last_wmi_command_output = Field(str, 'Last WMI Command Output')
    backup_source = Field(str, 'Backup Source')

    required = ['name', 'hostname', 'os', 'network_interfaces']

    def generate_direct_connected_devices(self):
        try:
            for connected_device in self.connected_devices:
                if (hasattr(connected_device, 'connection_type') and
                        connected_device.connection_type == ConnectionType.Direct.name) or \
                        (isinstance(connected_device, 'dict') and 'connection_type' in connected_device and
                         connected_device['connection_type'] == ConnectionType.Direct.name):
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
            if ipaddress.ip_address(ip).is_private:
                logger.warning(f'add_public_ip: got {ip} which is private, bypassing')
                return
        except Exception:
            logger.exception(f'Error: could not parse ip {ip}')
            return
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
        try:
            raw_data = replace_large_ints(raw_data)
        except Exception:
            logger.exception('Failed to replace raw data large ints')
            return
        raw_data = escape_dict(raw_data)
        try:
            data_size = len(str(raw_data))
            if data_size > MAX_SIZE_OF_MONGO_DOCUMENT:
                logger.error(f'Size of raw data is too large: {data_size} MB')
                return
        except Exception:
            logger.exception('Failed to ascertain size of raw data')
            return
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
                logger.warning(f'Invalid ips: {repr(ips)}', exc_info=True)
            else:
                for ip in ips_iter:
                    try:
                        if ip and isinstance(ip, str) and ip != '0.0.0.0':
                            obj.ips.append(ip)
                            obj.ips_raw.append(ip)
                    except (ValueError, TypeError):
                        if logger is None:
                            raise
                        logger.warning(f'Invalid ip: {repr(ip)}', exc_info=True)
        if subnets is not None:
            try:
                subnets_iter = iter(subnets)
            except TypeError:
                if logger is None:
                    raise
                logger.warning(f'Invalid subnets: {repr(subnets)}', exc_info=True)
            else:
                for subnet in subnets_iter:
                    try:
                        subnet = format_subnet(subnet)  # formatting here just to make sure we don't add duplicates...
                        if subnet not in obj.subnets:
                            obj.subnets.append(subnet)
                    except (ValueError, TypeError):
                        if logger is None:
                            raise
                        logger.warning(f'Invalid subnet: {repr(subnet)}', exc_info=True)
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
            logger.warning(f'failed to handle mac {macs} {te}')
            macs = []

        if ips and isinstance(ips, (str, bytes)):
            ips = [ips]

        # Validate list, throw other
        try:
            ips = list(ips)
        except TypeError as te:
            logger.warning(f'failed to handle ips {ips} {te}')
            ips = []

        # If only one mac assume the ips are related and just add nic
        if macs and len(macs) == 1:
            try:
                self.add_nic(macs[0], ips)
            except Exception:
                logger.warning(f'Failed to add macs and ips {macs} {ips}', exc_info=True)
            return

        # multiple mac, assume different interfaces
        for mac in macs:
            try:
                self.add_nic(mac=mac)
            except Exception:
                logger.warning(f'Failed to add mac {mac}', exc_info=True)

        for ip in ips:
            try:
                self.add_nic(ips=[ip])
            except Exception:
                logger.warning(f'Failed to add ip {ip}', exc_info=True)

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
                logger.warning(f'Invalid name: {repr(name)}', exc_info=True)

        if port is not None:
            try:
                nic.port = port
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid port: {repr(port)}', exc_info=True)
        if mtu is not None:
            try:
                nic.mtu = int(mtu)
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid mtu: {repr(mtu)}', exc_info=True)

        if speed is not None:
            try:
                nic.speed = speed
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid speed: {repr(speed)}', exc_info=True)

        if operational_status is not None:
            try:
                nic.operational_status = operational_status
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid operational_status: {repr(operational_status)}', exc_info=True)

        if admin_status is not None:
            try:
                nic.admin_status = admin_status
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid admin_status: {repr(admin_status)}', exc_info=True)

        if port_type is not None:
            try:
                nic.port_type = port_type
            except (ValueError, TypeError):
                if logger is None:
                    raise
                logger.warning(f'Invalid port_type: {repr(port_type)}', exc_info=True)

        if vlans is not None:
            try:
                nic.vlan_list = vlans
            except Exception:
                if logger is None:
                    raise
                logger.warning(f'Invalid vlans: {repr(vlans)}', exc_info=True)

        if gateway is not None:
            try:
                nic.gateway = gateway
            except Exception:
                if logger is None:
                    raise
                logger.warning(f'Invalid gateway: {repr(vlans)}', exc_info=True)

        self.network_interfaces.append(nic)

    def figure_os(self, os_string, guess=False):

        os_dict = figure_out_os(str(os_string))
        if os_dict is None:
            return

        try:
            if guess:
                old_dict = copy.copy(self.os_guess.to_dict())
            else:
                old_dict = copy.copy(self.os.to_dict())
            for key, value in os_dict.items():
                if value:
                    old_dict[key] = value
            os_dict = old_dict
        except Exception:
            pass

        if guess:
            self.os_guess = DeviceAdapterOS(**os_dict)
        else:
            self.os = DeviceAdapterOS(**os_dict)

    def add_battery(self, **kwargs):
        self.batteries.append(DeviceAdapterBattery(**kwargs))

    def add_local_admin(self, **kwargs):
        try:
            admin_name = kwargs.get('admin_name')
            if not admin_name:
                return
            if kwargs.get('admin_type') == 'Admin User':
                self.local_admins_users.append(admin_name)
            elif kwargs.get('admin_type') == 'Group Membership':
                self.local_admins_groups.append(admin_name)
        except Exception:
            pass
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
        # Note! this is not just an 'MSRC' available patch. Its for all OS's.
        # But i do not want to refactor the name right now.
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
            'i486': 'x86',
            'i586': 'x86',
            'i686': 'x86',
            'i786': 'x86',
            '32-bit': 'x86',
            'noarch': 'all',
            'none': 'all',
            '(none)': 'all',
        }

        if 'architecture' in kwargs and kwargs['architecture'] in arch_translate_dict:
            kwargs['architecture'] = arch_translate_dict[kwargs['architecture']]

        version_raw = ''
        version = kwargs.get('version')
        name = kwargs.get('name')
        if version:
            version = version.strip()
            version_raw = parse_versions_raw(version) or ''
            kwargs['version'] = version
        name_version = None
        if name and version:
            name_version = f'{name}-{version}'

        self.installed_software.append(DeviceAdapterInstalledSoftware(
            version_raw=version_raw, name_version=name_version, **kwargs))

    def add_vulnerable_software(self, cvss=None, **kwargs):
        cvss_str = None
        if cvss:
            try:
                cvss = float(cvss)
                cvss_str = f'CVSS {str(cvss)}'
            except Exception:
                logger.exception(f'Invalid cvss {cvss}')
                return
        else:
            cvss = None

        version_raw = ''
        try:
            if 'software_version' in kwargs:
                version_raw = parse_versions_raw(kwargs['software_version'])
        except Exception:
            logger.exception('Problem parsing raw version')

        self.software_cves.append(DeviceAdapterSoftwareCVE(cvss_str=cvss_str,
                                                           cvss=cvss, version_raw=version_raw, **kwargs))

    def add_key_value_tag(self, key, value):
        self.tags.append(DeviceTagKeyValue(tag_key=key, tag_value=value))

    def add_agent_version(self, agent=None, version=None, status=None):
        if not version and not status:
            return
        if not version:
            version = None
        if not status:
            status = None
        try:
            self.agent_versions.append(DeviceAdapterAgentVersion(adapter_name=agent,
                                                                 agent_version=version,
                                                                 agent_version_raw=parse_versions_raw(version),
                                                                 agent_status=status))
        except Exception:
            logger.exception(f'Problem adding agent version for {agent} {version}')

    def set_shodan_data(self, **kwargs):
        self.shodan_data = ShodanData(**kwargs)

    def add_open_port(self, protocol=None, port_id=None, service_name=None):
        if port_id:
            try:
                port_id = int(port_id)
                if port_id > 0xffff or port_id < 0:
                    logger.error(f'Invalid port id given {port_id}')
                    return
            except Exception:
                logger.error(f'Invalid port id given {port_id}')
                return
        if protocol:
            try:
                protocol = protocol.upper()
            except Exception:
                logger.exception(f'Error converting protocol {protocol}')
        if service_name and not isinstance(service_name, (str, bytes)):
            return
        if not any([port_id, service_name]):
            logger.debug('Skipping empty port')
            return
        open_port = DeviceOpenPort(protocol=protocol,
                                   port_id=port_id,
                                   service_name=service_name)
        self.open_ports.append(open_port)

    def add_swap_file(self, name, size_in_gb):
        self.swap_files.append(DeviceSwapFile(name=name, size_in_gb=size_in_gb))

    def add_share(self, **kwargs):
        self.shares.append(ShareData(**kwargs))

    def add_process(self, **kwargs):
        self.processes.append(ProcessData(**kwargs))

    def add_service(self, **kwargs):
        self.services.append(ServiceData(**kwargs))

    def add_firewall_rule(self, **kwargs):
        self.firewall_rules.append(FirewallRule(**kwargs))


NETWORK_INTERFACES_FIELD = DeviceAdapter.network_interfaces.name
LAST_SEEN_FIELD = DeviceAdapter.last_seen.name
LAST_SEEN_FIELDS = [LAST_SEEN_FIELD, 'ssm_data_last_seen', 'last_sign_in']
OS_FIELD = DeviceAdapter.os.name

MAC_FIELD = DeviceAdapterNetworkInterface.mac.name
IPS_FIELD = DeviceAdapterNetworkInterface.ips.name
