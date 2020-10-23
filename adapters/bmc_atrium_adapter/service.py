import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.bmc_atrium.connection import BmcAtriumConnection
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from bmc_atrium_adapter.client_id import get_client_id
from bmc_atrium_adapter.structures import BmcAtriumDeviceInstance

logger = logging.getLogger(f'axonius.{__name__}')


class BmcAtriumAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(BmcAtriumDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = BmcAtriumConnection(domain=client_config.get('domain'),
                                         verify_ssl=client_config.get('verify_ssl'),
                                         https_proxy=client_config.get('https_proxy'),
                                         proxy_username=client_config.get('proxy_username'),
                                         proxy_password=client_config.get('proxy_password'),
                                         username=client_config.get('username'),
                                         password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            if 'Max retries exceeded with' in str(e):
                message = f'Server {0} is unreachable'.format(client_config.get('domain'))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema BmcAtriumAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
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
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
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

    @staticmethod
    def _fill_bmc_atrium_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.subnet_type = device_raw.get('SubnetType')
            device.subnet_name = device_raw.get('SubnetName')
            device.country = device_raw.get('Country')
            device.ud_root_last_access_time = parse_date(device_raw.get('UDRootLastAccessTime'))
            device.vm_power_status = device_raw.get('VM_PowerStatus')
            device.managed_by_dl = device_raw.get('ManagedBy_DL')
            device.device_type = device_raw.get('DeviceType')
            device.global_id = device_raw.get('GlobalID')
            device.bu = device_raw.get('BU')
            device.owner_code = device_raw.get('OwnerCode')
            device.account = device_raw.get('Account')
            device.bdna_model = device_raw.get('BDNAModel')
            device.it_customer = device_raw.get('ITCustomer')
            device.custom_region = device_raw.get('Custom_Region')
            device.cc_team_leader = device_raw.get('CC_Team_Leader')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.id = (device_raw.get('Name') or '') + '_' + (device_raw.get('Serial Number') or '')
            device.name = device_raw.get('Name')
            if device_raw.get('PrimaryIPAddress'):
                device.add_nic(ips=[device_raw.get('PrimaryIPAddress')])
            device.device_serial = device_raw.get('Serial Number')
            device.figure_os(device_raw.get('OSType'))
            device.owner = device_raw.get('Owner_name')
            self._fill_bmc_atrium_device_fields(device_raw, device)
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching BmcAtrium Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching BmcAtrium Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
