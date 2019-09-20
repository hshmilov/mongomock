# pylint: disable=import-error
import logging
import xml.etree.ElementTree as ET
from zeep import Client


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from ca_cmdb_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')

MAX_ROWS_FLOOD_NUM = 1000000


class CaCmdbAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def get_connection(client_config):
        domain = RESTConnection.build_url(client_config['domain']).strip('/')
        wsdl = f'{domain}/axis/services/USD_R11_WebService?wsdl'
        client = Client(wsdl=wsdl)
        sid = client.service.login(client_config['username'], client_config['password'])
        data = client.service.doQuery(
            sid=sid,
            objectType='nr',
            whereClause=(
                'delete_flag = 0 '
                'and serial_number is not null '
            ),
        )
        return client, sid, data

    def _connect_client(self, client_config):
        client = None
        data = None
        sid = None
        try:
            client, sid, data = self.get_connection(client_config)
            return client_config
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)
        finally:
            if client and data and sid:
                list_handle = data['listHandle']
                client.service.freeListHandles(sid=sid,
                                               handles=[list_handle])
                client.service.logout(sid=sid)

    # pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client, sid, data = self.get_connection(client_data)
        try:
            list_handle = data['listHandle']
            list_length = data['listLength']
            max_rows = 250
            current = 1

            while current <= min(list_length, MAX_ROWS_FLOOD_NUM):
                try:
                    data = client.service.getListValues(
                        sid=sid,
                        listHandle=list_handle,
                        startIndex=current,
                        endIndex=current + max_rows - 1,
                        attributeNames={
                            'string': [
                                'serial_number',  # serial number
                                'family.sym',  # what type of device it is
                                'name',  # asset name as its listed in SDM
                                'alarm_id',  # ip address
                            ]
                        }
                    )
                    xml_data = ET.fromstring(data)
                    if not xml_data.tag == 'UDSObjectList':
                        logger.error(f'Bad first tag {xml_data.tag}')
                        break
                    for xml_object in xml_data:
                        try:
                            if not xml_object.tag == 'UDSObject':
                                logger.error(f'Bad object tag {xml_object.tag}')
                                continue
                            xml_attributes = xml_object[1]
                            if not xml_attributes.tag == 'Attributes':
                                logger.error(f'Bad Attributes tag {xml_attributes.tag}')
                                continue
                            device_raw = dict()
                            for xml_attribute in xml_attributes:
                                try:
                                    if xml_attribute[0].tag == 'AttrName' and xml_attribute[1].tag == 'AttrValue':
                                        device_raw[xml_attribute[0].text] = xml_attribute[1].text
                                except Exception:
                                    logger.exception(f'Problem with xml attribute')
                            yield device_raw
                        except Exception:
                            logger.exception(f'Problem with xml object')
                    current = current + max_rows
                except Exception:
                    logger.exception(f'Problem with current {current}')
                    break
        finally:
            client.service.freeListHandles(sid=sid,
                                           handles=[list_handle])
            client.service.logout(sid=sid)

    @staticmethod
    def _clients_schema():
        """
        The schema CaCmdbAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CA CMDB Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'domain',
                'username',
                'password',
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('serial_number')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')
            device.name = device_raw.get('name')
            device.device_serial = device_raw.get('serial_number')
            device.device_type = device_raw.get('family.sym')
            if device_raw.get('alarm_id') and device_raw.get('alarm_id').strip().lower() not in ['test',
                                                                                                 'dhcp',
                                                                                                 'undefined',
                                                                                                 'ipaddress',
                                                                                                 'na']:
                device.add_nic(ips=device_raw.get('alarm_id').strip().split(','))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CaCmdb Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
