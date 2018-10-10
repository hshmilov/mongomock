import json
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from datadog_adapter.connection import DatadogConnection

logger = logging.getLogger(f'axonius.{__name__}')


class DatadogAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        python_version = Field(str, 'Python Version')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    def _get_client_id(self, client_config):
        return client_config['domain']

    def _connect_client(self, client_config):
        try:
            connection = DatadogConnection(domain=client_config['domain'],
                                           verify_ssl=client_config.get('verify_ssl', False),
                                           appkey=client_config['appkey'], apikey=client_config['apikey'],
                                           https_proxy=client_config.get('https_proxy'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific datadog domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a datadog connection

        :return: A json with all the attributes returned from the datadog Server
        """
        with client_data:
            yield from client_data.get_device_list()

    def _clients_schema(self):
        """
        The schema datadogAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Datadog Domain',
                    'type': 'string'
                },
                {
                    'name': 'appkey',
                    'title': 'Application Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },

                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },

            ],
            'required': [
                'domain',
                'appkey',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('id')
                if not device_id:
                    logger.warning(f'Bad device with no ID {device_id}')
                    continue
                device.id = str(device_id) + (device_raw.get('name') or '')
                device.name = device_raw.get('name')
                device.hostname = device_raw.get('host_name')
                try:
                    for app in device_raw.get('apps') or []:
                        device.add_installed_software(name=app)
                except Exception:
                    logger.exception(f'Problem adding apps to device {device_raw}')

                try:
                    gohai = json.loads((device_raw.get('meta') or {}).get('gohai') or '{}')
                    try:
                        network = gohai.get('network') or {}
                        ips = []
                        if network.get('ipaddress'):
                            ips.append(network.get('ipaddress'))
                        if network.get('ipaddressv6'):
                            ips.append(network.get('ipaddressv6'))
                        mac = None
                        if network.get('macaddress'):
                            mac = network.get('macaddress')
                        if mac or ips:
                            device.add_nic(mac, ips)
                    except Exception:
                        logger.exception(f'Problem adding nic to {device_raw}')
                    platform = gohai.get('platform') or {}
                    device.python_version = platform.get('pythonV')
                    os_raw = (platform.get('kernel_name') or '') + ' ' + (platform.get('os') or '') \
                        + ' ' + (platform.get('processor') or '')
                    device.figure_os(os_raw)
                    device.agent_version = (device_raw.get('meta') or {}).get('agent_version')
                except Exception:
                    logger.exception(f'Problem getting ohai at {device_raw}')

                aws_id = device_raw.get('aws_id')
                if aws_id:
                    device.cloud_provider = 'AWS'
                    device.cloud_id = aws_id

                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception('Problem with fetching datadog Device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
