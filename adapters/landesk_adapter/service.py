# pylint: disable=import-error
import ipaddress
import logging
from requests import Session
from requests_ntlm import HttpNtlmAuth
from zeep import Client
from zeep.transports import Transport  # pylint: disable=import-error


from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import is_domain_valid
from axonius.utils.files import get_local_config_file
from landesk_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class LandeskAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        pass

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
        session = Session()
        session.auth = HttpNtlmAuth(client_config['username'], client_config['password'])
        session.verify = False
        domain = RESTConnection.build_url(client_config['domain']).strip('/')
        wsdl = f'{domain}/MBSDKService/MsgSDK.asmx?WSDL'
        session.get(wsdl, verify=False)
        client = Client(wsdl, transport=Transport(session=session))
        return client

    def _connect_client(self, client_config):
        try:
            self.get_connection(client_config)
            return client_config
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    # pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client = self.get_connection(client_data)
        return client.service.ListMachines('')

    @staticmethod
    def _clients_schema():
        """
        The schema LandeskAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Ivanti UEM Domain',
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
            device_id = device_raw.get('GUID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('DeviceName') or '')
            device.hostname = device_raw.get('DeviceName')
            ip = device_raw.get('IPAddress')
            try:
                ip = str(ipaddress.ip_address(ip))
                ips = [ip]
            except Exception:
                ips = None
            mac = device_raw.get('MACAddress')
            if not mac:
                mac = None
            if mac or ips:
                device.add_nic(ips=ips, mac=mac)
            domain = device_raw.get('DomainName')
            if is_domain_valid(domain):
                device.domain = domain
            device.figure_os(device_raw.get('OSName'))
            if device_raw.get('LastLogin'):
                device.last_used_users.append(device_raw.get('LastLogin'))
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Landesk Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        if devices_raw_data is None:
            return
        for device_raw in devices_raw_data['Devices']['Device']:
            device = self._create_device(device_raw.__dict__['__values__'])
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
