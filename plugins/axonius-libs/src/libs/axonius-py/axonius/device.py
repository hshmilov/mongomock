import datetime
import typing

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.parsing_utils import figure_out_os
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.mongo_escaping import escape_dict


"""
    For adding new fields, see https://axonius.atlassian.net/wiki/spaces/AX/pages/398819372/Adding+New+Field
"""


class DeviceOS(SmartJsonClass):
    """ A definition for the json-scheme for an OS (of a device) """
    type = Field(str, 'OS', enum=['Windows', 'Linux', 'OS X', 'iOS', 'Android'])
    distribution = Field(str, 'OS Distribution')
    bitness = Field(int, 'OS Bitness', enum=[32, 64])

    major = Field(str, 'OS Major')
    minor = Field(str, 'OS Minor')


class NetworkInterface(SmartJsonClass):
    """ A definition for the json-scheme for a network interface """
    mac = Field(str, 'Mac')
    ip = ListField(str, 'IPs')


class Device(SmartJsonClass):
    """ A definition for the json-scheme for a Device """

    name = Field(str, 'Device Name')
    hostname = Field(str, 'Host Name', json_format=JsonStringFormat.hostname)
    id = Field(str, 'ID')
    os = Field(DeviceOS, 'OS')
    last_seen = Field(datetime.datetime, 'Last Seen', json_format=JsonStringFormat.date_time)
    network_interfaces = ListField(NetworkInterface, 'Network Interfaces')
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

    def add_nic(self, mac=None, ip=None):
        """
        Add a new network interface card to this device.
        :param mac: the mac
        :param ip: an IP list
        """
        self.network_interfaces.append(NetworkInterface(mac=mac, ip=ip))

    def figure_os(self, os_string):
        os_dict = figure_out_os(os_string)
        if os_dict is None:
            return
        self.os = DeviceOS(**os_dict)


NETWORK_INTERFACES_FIELD_NAME = Device.network_interfaces.name
SCANNER_FIELD_NAME = Device.scanner.name
LAST_SEEN_FIELD_NAME = Device.last_seen.name
