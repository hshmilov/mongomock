import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from ca_spectrum_adapter.connection import CaSpectrumConnection
from ca_spectrum_adapter.client_id import get_client_id
from ca_spectrum_adapter.consts import XML_ATTRIB_CODES

logger = logging.getLogger(f'axonius.{__name__}')


class CaSpectrumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        notes = Field(str, 'Notes')
        ca_type = Field(str, 'Device Type')
        contact_person = Field(str, 'Contact Person')
        location = Field(str, 'Location')

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
        connection = CaSpectrumConnection(domain=client_config['domain'],
                                          verify_ssl=client_config['verify_ssl'],
                                          https_proxy=client_config.get('https_proxy'),
                                          username=client_config['username'],
                                          password=client_config['password'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema CaSpectrumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CA Spectrum Domain',
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
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_raw_dict = dict()
            device_raw_dict['id'] = device_raw.attrib.get('mh')
            for xml_attrib in device_raw:
                try:
                    if xml_attrib.tag != 'attribute':
                        continue
                    attrib_id = xml_attrib.attrib.get('id')
                    if attrib_id not in XML_ATTRIB_CODES:
                        continue
                    device_raw_dict[XML_ATTRIB_CODES[attrib_id]] = xml_attrib.text
                except Exception:
                    logger.exception('Problem with xml attrib')
            device_id = device_raw_dict.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw_dict}')
                return None
            device.id = str(device_id) + '_' + (device_raw_dict.get('Model Name') or '')
            device.hostname = device_raw_dict.get('Model Name')
            ips = device_raw_dict.get('Network_Address').split(',') if\
                (device_raw_dict.get('Network_Address') and
                 isinstance(device_raw_dict.get('Network_Address'), str)) else None
            mac = device_raw_dict.get('MAC_Address')
            if not mac:
                mac = None
            if mac or ips:
                device.add_nic(mac=mac, ips=ips)
            try:
                if device_raw_dict.get('Mdl_creat_time'):
                    device.first_seen = parse_date(int(device_raw_dict.get('Mdl_creat_time')))
            except Exception:
                logger.exception(f'Problem getting first seen for {device_raw_dict}')
            device.contact_person = device_raw_dict.get('ContactPerson')
            device.notes = device_raw_dict.get('Notes')
            device.device_manufacturer = device_raw_dict.get('Manufacturer')
            device.device_serial = device_raw_dict.get('Serial_Number')
            device.description = device_raw_dict.get('sysDescr')
            device.location = device_raw_dict.get('Location')
            device.ca_type = device_raw_dict.get('DeviceType')
            device.set_raw(device_raw_dict)
            return device
        except Exception:
            logger.exception(f'Problem with fetching CaSpectrum Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
