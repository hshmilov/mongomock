import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from defender_atp_adapter.connection import DefenderAtpConnection
from defender_atp_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class DefenderAtpAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        group_name = Field(str, 'Group Name')
        risk_score = Field(str, 'Risk Score')
        exposure_level = Field(str, 'Exposure Level')
        machine_tags = ListField(str, 'Machine Tags')
        health_status = Field(str, 'Health Status')
        aad_device_id = Field(str, 'AzureAD Device ID')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability('https://login.windows.net',
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = DefenderAtpConnection(tenant_id=client_config['tenant_id'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           client_id=client_config['client_id'],
                                           client_secret=client_config['client_secret'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['tenant_id'], str(e))
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
        The schema DefenderAtpAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'tenant_id',
                    'title': 'Tenant ID',
                    'type': 'string'
                },
                {
                    'name': 'client_id',
                    'title': 'Client ID',
                    'type': 'string'
                },
                {
                    'name': 'client_secret',
                    'title': 'Client Secret',
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
                'tenant_id',
                'client_id',
                'client_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('computerDnsName') or '')
            device.hostname = device_raw.get('computerDnsName')
            device.first_seen = parse_date(device_raw.get('firstSeen'))
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.figure_os(device_raw.get('osPlatform'))
            try:
                device.os.build = device_raw.get('osBuild')
            except Exception:
                pass
            if device_raw.get('lastIpAddress'):
                device.add_nic(ips=[device_raw.get('lastIpAddress')])
            device.group_name = device_raw.get('rbacGroupName')
            device.risk_score = device_raw.get('riskScore')
            device.exposure_level = device_raw.get('exposureLevel')
            device.machine_tags = device_raw.get('machineTags')\
                if isinstance(device_raw.get('machineTags'), list) else None
            device.health_status = device_raw.get('healthStatus')
            device.part_of_domain = device_raw.get('isAadJoined')
            device.aad_device_id = device_raw.get('aadDeviceId')
            try:
                users_raw = device_raw.get('users_raw')
                if users_raw:
                    device.last_used_users = [user_raw.get('id') for user_raw in users_raw]
            except Exception:
                logger.exception(f'Problem adding users to {device_raw}')
            try:
                apps_raw = device_raw.get('apps_raw')
                if apps_raw:
                    for app_raw in apps_raw:
                        device.add_installed_software(name=app_raw.get('name'),
                                                      vendor=app_raw.get('vendor'))
            except Exception:
                logger.exception(f'Problem adding apps to {device_raw}')
            try:
                vulns_raw = device_raw.get('vulns_raw')
                if vulns_raw:
                    for vuln_raw in vulns_raw:
                        device.add_vulnerable_software(cve_id=vuln_raw.get('name'))
            except Exception:
                logger.exception(f'Problem adding vulns_raw to {device_raw}')
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching DefenderAtp Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent, AdapterProperty.Endpoint_Protection_Platform]
