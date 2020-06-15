import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class IncidentData(SmartJsonClass):
    scope = Field(str, 'Scope')
    type = Field(str, 'Type')
    sub_type = Field(str, 'Sub Type')
    severity = Field(str, 'Severity')
    title = Field(str, 'Title')
    published = Field(datetime.datetime, 'Published')
    closed_source = Field(bool, 'Closed Source')


class BasicShadowData(SmartJsonClass):
    reverse_domain_name = Field(str, 'Reverse Domain Name')
    incident = Field(IncidentData, 'Incident')


class PortInfo(BasicShadowData):
    discovered_open = Field(datetime.datetime, 'Discovered Open')
    detected_closed = Field(datetime.datetime, 'Detected Closed')
    port_number = Field(int, 'Port Number')
    transport = Field(str, 'Transport')


class VulnInfo(BasicShadowData):
    cve_id = Field(str, 'CVE Id')
    discovered = Field(datetime.datetime, 'Discovered')
    determined_resolved = Field(datetime.datetime, 'Determined Resolved')


class SocketInfo(BasicShadowData):
    domain_name = Field(str, 'Domain Name')
    transport = Field(str, 'Transport')
    discovered = Field(datetime.datetime, 'Discovered')
    grade = Field(str, 'Grade')
    certificate_common_name = Field(str, 'Certificate Common Name')
    revoked = Field(bool, 'Revoked')
    expires = Field(datetime.datetime, 'Expires')
    issues = ListField(str, 'Issues')


class DigitalShadowsDeviceInstance(DeviceAdapter):
    digital_shadows_ports_info = ListField(PortInfo, 'Digital Shadows Ports Information')
    digital_shadows_vulns_info = ListField(VulnInfo, 'Digital Shadows Vulnerabilities Information')
    digital_shadows_socket_info = ListField(SocketInfo, 'Digital Shadows Socket Information')
