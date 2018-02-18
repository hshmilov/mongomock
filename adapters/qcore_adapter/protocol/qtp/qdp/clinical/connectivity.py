from enum import auto
from construct import Struct, Byte, Enum, Embedded

from qcore_adapter.protocol.qtp.common import QcoreString, enum_to_mapping, CStyleEnum


class ConnectionState(CStyleEnum):
    NoNetwork = auto()
    EthernetNoMednet = auto()
    EthernetMednet = auto()
    WirelessNoMednet = auto()
    WirelessMednet = auto()


ConnectionStateReverseMapping = enum_to_mapping(ConnectionState)

WirelessInfo = Struct(
    # ip, net, gateway
    'ip_address' / QcoreString,
    'netmask' / QcoreString,
    'gateway' / QcoreString,

    # mac, dhcp
    'mac' / QcoreString,
    'dhcp_enables' / Byte,

    # wifi-level data
    'noise_level' / QcoreString,
    'ssid' / QcoreString,
    'bssid' / QcoreString,
    'wireless_strenght' / Byte,
    'channel_bandwith' / QcoreString,
    'channel' / QcoreString,
    'tx_rate' / QcoreString,
    'auth_method' / QcoreString,
    'wpa_encrypt' / QcoreString,
    'band' / QcoreString,
    'transmit_power' / QcoreString
)

ConnectivityClinicalStatus = Struct(
    'connection_state' / Enum(Byte, **ConnectionStateReverseMapping),
    'networks_status' / Embedded(WirelessInfo)
)
