from enum import Enum, auto

COMMAND_API = 'command-api'
ARP_INFO = 'arp_info'
BASIC_INFO = 'basic_info'


class AristaEOSCommads(Enum):
    enable = 'enable'
    show_arp = 'show arp'
    show_version = 'show version'
    show_hostname = 'show hostname'
    show_interfaces = 'sh interfaces'


class FetchProto(Enum):
    ARP = auto()
    BASIC_INFO = auto()
