from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass


# pylint: disable=too-many-instance-attributes
class AccessRule(SmartJsonClass):
    action_from = Field(str, 'From')
    action_to = Field(str, 'To')
    action = Field(str, 'Action')
    uuid = Field(str, 'UUID')
    name = Field(str, 'Name')
    comment = Field(str, 'Comment')
    enable = Field(bool, 'Enable')
    reflexive = Field(bool, 'Reflexive')
    max_connections = Field(int, 'Max Connections')
    logging = Field(bool, 'Logging')
    sip = Field(bool, 'sip')
    h323 = Field(bool, 'h323')
    management = Field(bool, 'Management')
    packet_monitoring = Field(bool, 'Packet Monitoring')
    fragments = Field(bool, 'Fragments')
    botnet_filter = Field(bool, 'BotNet Filter')
    dpi = Field(bool, 'DPI')
    single_sign_on = Field(bool, 'Single Sign On')
    block_traffic = Field(bool, 'Block Traffic For Single Sign On')
    redirect_unauthenticated_users = Field(bool, 'Redirect Unauthenticated Users To Log In')
    flow_reporting = Field(bool, 'Flow Reporting')
    cos_override = Field(bool, 'COS Override')
    source = Field(str, 'Source')
    destination = Field(str, 'Destination')
    port = Field(str, 'Port Name')
    service = Field(str, 'Service')
    users_included = Field(str, 'Users Included')
    users_excluded = Field(str, 'Users Excluded')
    connection_source_limit = Field(int, 'Connection Source Limit')
    connection_destination_limit = Field(int, 'Connection Destination Limit')


# pylint: disable=too-many-instance-attributes
class SonicWallInterfaceInstance(SmartJsonClass):
    vlan = Field(int, 'Interface VLAN ID')
    tunnel = Field(int, 'WLAN Tunnel Interface ID')
    comment = Field(str, 'Comment')
    http_management = Field(bool, 'Enable HTTP Management')
    https_management = Field(bool, 'Enable HTTPS Management')
    ping_management = Field(bool, 'Enable Ping Management')
    snmp_management = Field(bool, 'Enable SNMP Management')
    ssh_management = Field(bool, 'Enable SSH Management')
    http_login = Field(bool, 'Enable HTTP Login')
    https_login = Field(bool, 'Enable HTTPS Login')
    https_redirect = Field(bool, 'Enable HTTP to HTTPS Redirection')
    send_icmp_fragmentation = Field(bool, 'Enable ICMP Fragmentation')
    fragment_packets = Field(bool, 'Enable Fragment non-VPN Outbound')
    auto_discovery = Field(bool, 'Enable Auto Discovery for SonicWall Switches')
    flow_reporting = Field(bool, 'Enable Flow Reporting')
    multicast = Field(bool, 'Enable Multicast Support')
    cos_8021p = Field(bool, 'Enable 802.1p Support')
    exclude_route = Field(bool, 'Enable Exclude From RouteAdvertisement')
    asymmetric_route = Field(bool, 'Enable Asymmetric Route')
    management_traffic_only = Field(bool, 'Enable Management Traffic Only')
    dns_proxy = Field(bool, 'Enable DNS Proxy')
    shutdown_port = Field(bool, 'Enable Shutdown Port')
    default_8021p_cos = Field(str, 'Enable Default 802.1p CoS')
    firewalling = Field(bool, 'Enable Firewalling With Other Bridge Members')


class SonicWallDeviceInstance(DeviceAdapter):
    zone = Field(str, 'Zone')
    muilti_homed = Field(bool, 'Multi Homed')
    interface_ipv4 = Field(SonicWallInterfaceInstance, 'IPV4 Interface')
    access_rules = ListField(AccessRule, 'Access Rules')
