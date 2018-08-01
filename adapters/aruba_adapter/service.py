import logging

from aruba_adapter import arubaapi
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


class ArubaAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type', enum=['Arp Device'])
        protocol = Field(str, 'Protocol')
        vlan = Field(str, 'Vlan')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        port = client_config.get('port')
        if port == '':
            port = None
        try:
            connection = arubaapi.ArubaAPI(device=client_config['domain'], username=client_config['username'],
                                           password=client_config['password'],
                                           insecure=not client_config.get('verify_ssl'),
                                           port=port)
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        with client_data:
            return client_data.cli('show arp')

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in list(devices_raw_data.get('T1', []))[1:]:
            try:
                device = self._new_device_adapter()
                device.device_type = 'Arp Device'
                # We assume that device_data_list starts with Protocol, IP Address and MacAddres and then VLAN
                # If no VLAN is attached we will put ''
                device_data_list = [data_from_xml.strip() for data_from_xml in device_raw.split('\t')]
                device_data_list = list(filter(lambda x: x != '', device_data_list))
                if len(device_data_list) < 3:
                    logger.error(f'Bad device data list {str(device_data_list)}')
                    continue
                if len(device_data_list) == 3:
                    logger.warning(f'No interface name for {str(device_data_list)}')
                    device_data_list.append('')
                device.id = device_data_list[2]
                try:
                    device.add_nic(mac=device_data_list[2])
                except Exception:
                    logger.exception(f'Problem adding nic to {str(device_data_list)}')
                try:
                    device.set_related_ips(ips=[device_data_list[1]])
                except Exception:
                    logger.exception(f'Problem adding linked device to {str(device_data_list)}')
                device.protocol = str(device_data_list[0])
                device.vlan = str(device_data_list[3])
                device.set_raw({'data': device_data_list})
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Aruba Device {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    def _clients_schema(self):
        """
        The schema ArubaAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Aruba Host',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
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

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        """
        To be implemented by inheritors, otherwise leave empty.
        :type correlation_cmd_result: str
        :param correlation_cmd_result: result of running cmd on a machine
        :type os_type: str
        :param os_type: the type of machine ran upon
        :return:
        """
        raise NotImplementedError()
