import ipaddress
import logging
import hashlib
import sys

from dsp3.models.manager import Manager

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.files import get_local_config_file
from deep_security_adapter.consts import LEGACY_API, DEFAULT_PORT, REST_API
from deep_security_adapter.connection import DeepSecurityConnection

logger = logging.getLogger(f'axonius.{__name__}')


def raise_not_exit(msg=''):
    raise Exception(msg)


class DeepSecurityAdapter(AdapterBase):
    DEFAULT_CONNECT_CLIENT_TIMEOUT = 1800

    class MyDeviceAdapter(DeviceAdapter):
        state = Field(str, 'Device running state')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        if client_config.get('username'):
            return (client_config.get('domain') or '') + (client_config.get('tenant') or '') + \
                client_config.get('username')
        api_declassified = hashlib.md5(client_config['rest_apikey'].encode('utf-8')).hexdigest()
        return client_config['domain'] + '_' + api_declassified

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'), port=client_config.get('port'))

    @staticmethod
    def __create_manager_from_config(client_config):
        # In case of an error dsp3 calls to exit(). We have to change this to an exception
        exit_func = sys.exit
        try:
            sys.exit = raise_not_exit
            if client_config.get('domain'):
                dsm = Manager(username=client_config['username'],
                              password=client_config['password'],
                              host=client_config['domain'],
                              port=client_config.get('port') or DEFAULT_PORT,
                              )
            else:
                dsm = Manager(username=client_config['username'],
                              password=client_config['password'],
                              tenant=client_config.get('tenant'),
                              verify_ssl=client_config.get('verify_ssl') or False)
            return dsm
        finally:
            sys.exit = exit_func

    @staticmethod
    def get_rest_connection(client_config):
        connection = DeepSecurityConnection(domain=client_config['domain'],
                                            port=client_config.get('port'),
                                            verify_ssl=client_config['verify_ssl'],
                                            https_proxy=client_config.get('https_proxy'),
                                            apikey=client_config['rest_apikey'],
                                            session_timeout=(5, 1800))
        with connection:
            pass
        return connection

    def _connect_rest_client(self, client_config):
        try:
            return self.get_rest_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _set_connection_type(client_config):
        if client_config.get('rest_apikey'):
            if not client_config.get('domain'):
                raise ClientConnectionException('Using REST API key requires entering Domain parameter')
            return REST_API
        if not client_config.get('username') or not client_config.get('password'):
            raise ClientConnectionException('Choose API key or Username+Password')
        if not client_config.get('domain') and not client_config.get('tenant'):
            raise ClientConnectionException('Using Legacy API requires entering Tenant or Domain')
        return LEGACY_API

    def _connect_client(self, client_config):
        device_type = self._set_connection_type(client_config)
        if device_type == LEGACY_API:
            return self._connect_legacy_client(client_config), device_type
        return self._connect_rest_client(client_config), device_type

    def _connect_legacy_client(self, client_config):
        try:
            dsm = self.__create_manager_from_config(client_config)
            dsm.end_session()
            return client_config
        except Exception as e:
            reason = str(e)
            if not reason:
                reason = 'Login Failed'
            message = 'Error connecting to client , reason: {0}'.format(reason)
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific DeepSecurity domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a DeepSecurity connection

        :return: A json with all the attributes returned from the DeepSecurity Server
        """
        connection, client_type = client_data
        if client_type == LEGACY_API:
            dsm = self.__create_manager_from_config(connection)
            devices = dsm.host_retrieve_all()
            dsm.end_session()
            for device_raw in devices:
                yield device_raw, LEGACY_API
        elif client_type == REST_API:
            with connection:
                for device_raw in connection.get_device_list():
                    yield device_raw, REST_API

    def _clients_schema(self):
        """
        The schema DeepSecurityAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'On-Premise DeepSecurity Domain',
                    'type': 'string'
                },                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'string',
                    'default': DEFAULT_PORT
                },
                {
                    'name': 'tenant',
                    'title': 'Tenant ID',
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
                    'name': 'rest_apikey',
                    'type': 'string',
                    'title': 'REST API Key',
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
            ],
            'type': 'array'
        }

    def _create_legacy_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_raw_dict = device_raw.__dict__
            device_raw = device_raw_dict.copy()
            for key in device_raw_dict:
                if '__' in key:
                    del device_raw[key]
            device_id = device_raw.get('ID')
            hostname_or_ip = device_raw.get('name')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (hostname_or_ip or '')
            device.name = device_raw.get('displayName')
            try:
                ip = str(ipaddress.ip_address(hostname_or_ip))
                device.add_nic(None, [ip])
            except Exception:
                device.hostname = hostname_or_ip
            device.description = device_raw.get('description')
            device.figure_os(device_raw.get('platform'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Device {device_raw}')
            return None

    def _create_rest_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('ID')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('hostName') or '')
            device.hostname = device_raw.get('displayName')
            device.description = device_raw.get('description')
            try:
                if device_raw.get('hostName') and ipaddress.ip_address(device_raw.get('hostName')):
                    device.add_nic(ips=[device_raw.get('hostName')])
            except Exception:
                pass
            try:
                nics = (device_raw.get('interfaces') or {}).get('interfaces')
                if not isinstance(nics, list):
                    nics = []
                for nic_raw in nics:
                    try:
                        device.add_nic(ips=nic_raw.get('IPs'), mac=nic_raw.get('MAC'), name=nic_raw.get('name'))
                    except Exception:
                        logger.exception(f'Problem getting nic {nic_raw}')
            except Exception:
                logger.exception(f'Problem getting nics')
            device.last_seen = parse_date(device_raw.get('lastAgentCommunication'))
            device.figure_os(device_raw.get('platform'))
            agent_status = None
            if isinstance(device_raw.get('computerStatus'), dict):
                agent_status = device_raw.get('computerStatus').get('agentStatus')
            device.add_agent_version(agent=AGENT_NAMES.deep_security,
                                     version=device_raw.get('agentVersion'),
                                     status=agent_status)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Device {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            device = None
            if device_type == LEGACY_API:
                device = self._create_legacy_device(device_raw)
            elif device_type == REST_API:
                device = self._create_rest_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Endpoint_Protection_Platform, AdapterProperty.Agent, AdapterProperty.Manager]
