import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid
from crowd_strike_adapter.connection import CrowdStrikeConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CrowdStrikeAdapter(AdapterBase):

    class MyDeviceAdapter(DeviceAdapter):
        agent_version = Field(str, 'Agent Version')
        external_ip = Field(str, 'External IP')
        policies = ListField(str, 'Policies')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def action(self, action_type):
        raise NotImplementedError()

    @staticmethod
    def _get_client_id(client_config):
        return client_config['domain'] + '_' + client_config['username']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            connection = CrowdStrikeConnection(domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
                                               username=client_config['username'], password=client_config['apikey'],
                                               https_proxy=client_config.get('https_proxy'),
                                               headers={'Content-Type': 'application/json',
                                                        'Accept': 'application/json'})
            with connection:
                pass  # check that the connection credentials are valid
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
        try:
            client_data.connect()
            yield from client_data.get_device_list()
        finally:
            client_data.close()

    @staticmethod
    def _clients_schema():
        """
        The schema the adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'CrowdStrike Domain',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
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
                'apikey',
                'veirfy_ssl'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('device_id')
                if not device_id:
                    continue
                device.id = device_id
                device.agent_version = device_raw.get('agent_version')
                mac_address = device_raw.get('mac_address')
                local_ip = device_raw.get('local_ip')
                if mac_address or local_ip:
                    try:
                        device.add_nic(mac_address, local_ip.split(',') if local_ip is not None else None)
                    except Exception:
                        logger.exception(f'Problem getting nic for {device_raw}')
                try:
                    hostname = device_raw.get('hostname')
                    domain = device_raw.get('machine_domain')
                    if not is_domain_valid(domain):
                        domain = None
                    device.domain = domain
                    device.hostname = hostname
                except Exception:
                    logger.exception(f'Problem getting hostname for {device_raw}')
                try:
                    device.figure_os((device_raw.get('platform_name') or '') +
                                     (device_raw.get('os_version') or ''))
                    device.os.distribution = device_raw.get('os_version')
                except Exception:
                    logger.exception(f'Problem getting OS for {device_raw}')
                try:
                    device.last_seen = parse_date(device_raw.get('last_seen'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                device.external_ip = device_raw.get('external_ip')
                device.device_manufacturer = device_raw.get('bios_manufacturer')
                try:
                    device.policies = [str(policty_key) for policty_key in device_raw.get('device_policies').keys()]
                except Exception:
                    logger.exception(f'Problem getting policies at {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching CrowdStrike Device {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
