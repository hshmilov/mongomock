from enum import Enum, auto

from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass


class DNSResolveStatus(Enum):
    Pending = auto()
    Resolved = auto()
    Failed = auto()


class DNSResolvableDevice(SmartJsonClass):
    dns_resolve_status = Field(DNSResolveStatus, 'DNS resolve status')
