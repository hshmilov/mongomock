import datetime
import logging

from axonius.smart_json_class import SmartJsonClass

from axonius.utils.parsing import format_ip, format_ip_raw

from axonius.utils.datetime import parse_date

from axonius.fields import Field, ListField, JsonStringFormat

from axonius.utils.xml2json_parser import Xml2Json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts import remote_file_consts
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils import remote_file_utils
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


class ExtendedAttribute(SmartJsonClass):
    name = Field(str, 'Name')
    val = Field(str, 'Value')


class HpNnmiXmlAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        status = Field(str, 'Status')
        management_mode = Field(str, 'Management Mode')
        system_contact = Field(str, 'System Contact')
        location = Field(str, 'Location')
        snmp_name = Field(str, 'Node SNMP Name')
        snmp_addr = Field(str, 'SNMP Address', converter=format_ip, json_format=JsonStringFormat.ip)
        snmp_addr_raw = Field(str, converter=format_ip_raw, hidden=True)
        system_object_id = Field(str, 'System Object ID')
        notes = Field(str, 'Notes')
        created = Field(datetime.datetime, 'Creation time')
        modified = Field(datetime.datetime, 'Last Modified')
        status_change = Field(datetime.datetime, 'Last Status Change')
        proto_ver = Field(str, 'Protocol Version')
        discovery_state = Field(str, 'Discovery State')
        device_description = Field(str, 'Device Description')
        device_category = Field(str, 'Device Category')
        capabilities = ListField(str, 'Capabilities')
        pwr_state = Field(str, 'Device Power State')
        last_state_change = Field(datetime.datetime, 'Last State Change')
        ext_attrs = ListField(ExtendedAttribute, 'Extended Attributes')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'HP_NNMI_XML_{client_config["user_id"]}'

    @staticmethod
    def _test_reachability(client_config):
        return remote_file_utils.test_file_reachability(client_config)

    def _connect_client(self, client_config):
        if self._test_reachability(client_config):
            return client_config
        raise ClientConnectionException(f'Failed to load data from {client_config}!')

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        file_name, xml_data = remote_file_utils.load_remote_data(client_data)
        logger.info('Loaded remote data. Converting XML to JSON...')
        xml_json = Xml2Json(xml_data).result
        logger.info('Data converted to JSON!')
        if isinstance(xml_json, list):
            logger.debug('XML json is a list!')
            yield from xml_json
        elif isinstance(xml_json, dict):
            logger.debug('XML JSON is a dict!')
            topo = xml_json.get('topo', {})
            nodes = topo.get('node', topo)
            if isinstance(nodes, list):
                yield from nodes
            elif isinstance(nodes, dict):
                yield from [nodes]
            else:
                raise ClientConnectionException(f'Failed to get nodes from {client_data}')

    @staticmethod
    def _clients_schema():
        """
        The schema HpNnmiXmlAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    # pylint:disable=too-many-statements, too-many-branches
    def _create_device(self, device_raw):
        device = self._new_device_adapter()
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            # generic Axonius stuff
            try:
                device.first_seen = parse_date(device_raw.get('nodecreatetime'))
                device.last_seen = parse_date(device_raw.get('nodemodifiedtime'))
            except Exception as e:
                logger.warning(f'Got {str(e)} trying to parse last and first seen for {device_raw}')

            device.device_model = device_raw.get('deviceModel')
            device.device_model_family = device_raw.get('deviceFamily')
            device.device_manufacturer = device_raw.get('deviceVendor')
            device.uuid = device_raw.get('uuid')
            device.description = device_raw.get('deviceDescription')
            device.hostname = device_raw.get('name')
            device.name = device_raw.get('shortname')
            device.device_managed_by = device_raw.get('contact')

            # try to parse IP
            snmp_ip = device_raw.get('nodesnmpaddress')
            if snmp_ip:
                try:
                    device.add_ips_and_macs(ips=[snmp_ip])
                except Exception:
                    logger.exception(f'Failed to set IP for {device_raw}')

            # HP NNMI specific stuff
            device.status = device_raw.get('status')
            device.management_mode = device_raw.get('managementMode')
            device.system_contact = device_raw.get('contact')
            device.location = device_raw.get('location')
            device.snmp_name = device_raw.get('nodesnmpsysname')
            try:
                device.snmp_addr = device_raw.get('nodesnmpaddress')
                device.snmp_addr_raw = device_raw.get('nodesnmpaddress')
            except Exception:
                logger.warning(f'Got {str(e)} trying to parse snmp address for {device_raw}')
            device.system_object_id = device_raw.get('systemObjectId')
            device.notes = device_raw.get('notes')

            try:
                device.created = parse_date(device_raw.get('nodecreatetime'))
            except Exception:
                logger.warning(f'Failed to parse create time for {device_raw}')

            try:
                device.modified = parse_date(device_raw.get('nodemodifiedtime'))
            except Exception:
                logger.warning(f'Failed to parse modified time for {device_raw}')

            try:
                device.status_change = parse_date(device_raw.get('nodelaststatuschange'))
            except Exception:
                logger.warning(f'Failed to parse status change time for {device_raw}')

            device.proto_ver = device_raw.get('protocolversion')
            device.discovery_state = device_raw.get('discoveryState')
            device.device_description = device_raw.get('deviceDescription')

            try:
                capabilities = device_raw.get('capabilities')
                if isinstance(capabilities, dict):
                    cap_list = capabilities.get('capability')
                    if cap_list and isinstance(cap_list, list):
                        device.capabilities = cap_list
            except Exception:
                logger.warning(f'Failed to set device capabilities for {device_raw}')

            device.pwr_state = device_raw.get('powerState')
            try:
                device.last_state_change = parse_date(device_raw.get('lastStateChange'))
            except Exception:
                logger.warning(f'Failed to parse last state change time for {device_raw}')

            # parse extended attributes
            ext_attrs_raw = device_raw.get('extendedAttributes')
            try:
                ext_attrs = self._parse_extended_attributes(ext_attrs_raw)
                if ext_attrs:
                    device.ext_attrs = ext_attrs
            except Exception as e:
                logger.warning(f'Failed to parse extended attributes for device {device_id}: {str(e)}')
                logger.debug(f'Failed to parse extended attributes for {device_raw}', exc_info=True)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching HpNnmi Device for {device_raw}')
            return None

    @staticmethod
    def _parse_extended_attributes(ext_attrs_raw):
        ext_attrs = list()
        if isinstance(ext_attrs_raw, dict):
            attrs_raw = ext_attrs_raw.get('attribute') or []
            if isinstance(attrs_raw, dict):
                attrs_raw = [attrs_raw]
            if attrs_raw and isinstance(attrs_raw, list):
                for attr_raw_dict in attrs_raw:
                    if not isinstance(attr_raw_dict, dict):
                        logger.warning(f'Unable to parse extended attribute: expected dict, '
                                       f'got {attr_raw_dict} instead.')
                        continue
                    attr_name = attr_raw_dict.get('name')
                    attr_val = attr_raw_dict.get('value')
                    try:
                        ext_attrs.append(ExtendedAttribute(name=attr_name, val=attr_val))
                    except Exception:
                        logger.warning(f'Failed to parse extended attribute from {attr_name}: {attr_val}')
            else:
                logger.warning(f'Failed to parse extended attributes from {attrs_raw}')
        return ext_attrs

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
