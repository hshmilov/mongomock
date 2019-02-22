import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.fields import Field
from cybereason_adapter.connection import CybereasonConnection
from cybereason_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class CybereasonAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        agent_status = Field(str, 'Agent Status')
        agent_version = Field(str, 'Agent Version')
        public_ip = Field(str, 'Public IP')
        site_name = Field(str, 'Site Name')
        ransomware_status = Field(str, 'Ransomware Status')
        isolated = Field(bool, 'Isolated')
        prevention_status = Field(str, 'Prevention Status')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with CybereasonConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      username=client_config['username'],
                                      password=client_config['password'],
                                      https_proxy=client_config.get('https_proxy')) as connection:
                return connection
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
        The schema CybereasonAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Cybereason Domain',
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

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                sensor_id = device_raw.get('sensorId')
                if not sensor_id:
                    logger.warning(f'Bad device with no id {sensor_id}')
                    continue
                try:
                    mac_raw = sensor_id.split('_')[-1]
                    if mac_raw and isinstance(mac_raw, str) and len(mac_raw) == 12:
                        device.add_nic(mac_raw, None)
                except Exception:
                    logger.exception('Problem getting MAC address')
                device.id = sensor_id + '_' + (device_raw.get('machineName') or '')
                device.name = device_raw.get('machineName')
                device.hostname = device_raw.get('fqdn') or device_raw.get('machineName')
                device.public_ip = device_raw.get('externalIpAddress')
                if device_raw.get('internalIpAddress'):
                    device.add_nic(None, [device_raw.get('internalIpAddress')])
                device.site_name = device_raw.get('siteName')
                device.ransomware_status = device_raw.get('ransomwareStatus')
                device.isolated = device_raw.get('isolated')
                agent_status = device_raw.get('status')
                device.agent_status = agent_status
                if agent_status == 'Online':
                    device.last_seen = datetime.datetime.utcnow()
                elif isinstance(device_raw.get('disconnectionTime'), int):
                    try:
                        device.last_seen = datetime.datetime.fromtimestamp(device_raw.get('disconnectionTime') / 1000)
                    except Exception:
                        logger.exception(f'Problem adding last seen to {device_raw}')
                device.prevention_status = device_raw.get('preventionStatus')
                device.figure_os((device_raw.get('osType') or '') + ' ' + (device_raw.get('osVersionType') or ''))

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Cybereason Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
