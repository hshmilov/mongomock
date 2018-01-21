from axonius.fields import Field
from axonius.smart_json_class import SmartJsonClass


class DNSResolvableDevice(SmartJsonClass):
    dns_resolve_status = Field(str, 'DNS resolve status')
