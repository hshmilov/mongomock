import json
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.parsing import is_domain_valid
from axonius.utils.files import get_local_config_file
from truefort_adapter.connection import TruefortConnection
from truefort_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class TruefortAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        opts = Field(str, 'Opts')
        group_id = Field(str, 'Group ID')
        last_update = Field(datetime.datetime, 'Last Update')
        create_time = Field(datetime.datetime, 'Create Time')
        applications = ListField(str, 'Applications')

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
        connection = TruefortConnection(domain=client_config['domain'],
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
        The schema TruefortAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Truefort Domain',
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
            device_id = device_raw.get('agentid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('fqdn') or '')
            domain = device_raw.get('domain')
            if is_domain_valid(domain):
                device.domain = domain
            device.hostname = device_raw.get('fqdn')
            ip = device_raw.get('ipAddress')
            if ip and isinstance(ip, str):
                device.add_nic(None, ip.split(','))
            try:
                device.figure_os((device_raw.get('operatingSystem') or '') + ' ' + (device_raw.get('osVersion') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')
            device.opts = device_raw.get('opts')
            device.group_id = device_raw.get('groupid')
            device.add_agent_version(agent=AGENT_NAMES.truefort,
                                     version=device_raw.get('version'),
                                     status=device_raw.get('status'))
            try:
                device.last_update = parse_date(device_raw.get('lastUpdate'))
            except Exception:
                logger.exception(f'Problem getting last update for {device_raw}')
            try:
                device.create_time = parse_date(device_raw.get('createTime'))
            except Exception:
                logger.exception(f'Problem getting create time for {device_raw}')
            try:
                apps_raw = device_raw.get('applications')
                if apps_raw and isinstance(apps_raw, str):
                    device.applications = list(json.loads(apps_raw).values())
            except Exception:
                logger.exception(f'Problem adding apps to {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Truefort Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
