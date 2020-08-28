import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import get_exception_string

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=no-self-use
class AmdDbAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        vlan_id = Field(str, 'VLAN ID')
        role = Field(str, 'Role')
        country = Field(str, 'Country')
        business_unit = Field(str, 'Business Unit')
        division_name = Field(str, 'Division Name')
        account_name = Field(str, 'Account Name')
        region = Field(str, 'Region')
        site_display_name = Field(str, 'Site Display Name')
        device_status = Field(str, 'Device Status')
        subnet_name = Field(str, 'Subnet Name')
        subnet_type = Field(str, 'Subnet Type')
        device_type = Field(str, 'Device Type')
        device_type_display_name = Field(str, 'Device Type Display Name')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return 'ABC'

    def _test_reachability(self, client_config):
        raise NotImplementedError

    def _connect_client(self, client_config):
        try:
            endpoints_connection = MSSQLConnection(database='SIMS3Reports',
                                                   server=client_config['endpoint_db_address'],
                                                   port=client_config['endpoint_db_port'],
                                                   devices_paging=self.__devices_fetched_at_a_time)
            endpoints_connection.set_credentials(username=client_config['endpoint_db_username'],
                                                 password=client_config['endpoint_db_password'])
            with endpoints_connection:
                pass  # check that the connection credentials are valid
            servers_connection = MSSQLConnection(database='ServerInfo',
                                                 server=client_config['servers_db_address'],
                                                 port=client_config['servers_db_port'],
                                                 devices_paging=self.__devices_fetched_at_a_time)
            servers_connection.set_credentials(username=client_config['servers_db_username'],
                                               password=client_config['servers_db_password'])
            with servers_connection:
                pass  # check that the connection credentials are valid

            amd_ip_connection = MSSQLConnection(database='AmdocsIP',
                                                server=client_config['amd_ip_db_address'],
                                                port=client_config['amd_ip_db_port'],
                                                devices_paging=self.__devices_fetched_at_a_time)
            amd_ip_connection.set_credentials(username=client_config['amd_ip_db_username'],
                                              password=client_config['amd_ip_db_password'])
            with amd_ip_connection:
                pass  # check that the connection credentials are valid

            return endpoints_connection, servers_connection, amd_ip_connection
        except Exception as err:
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name, client_data):
        endpoints_connection, servers_connection, amd_ip_connection = client_data
        endpoints_connection.set_devices_paging(self.__devices_fetched_at_a_time)
        try:
            with endpoints_connection:
                for device_raw in endpoints_connection.query('SELECT dbo.Employees.EmpId, dbo.Employees.EmpFirstName, '
                                                             'dbo.MachineOwner.ComputerName, '
                                                             'dbo.Employees.EmpLastName, dbo.Employees.EmpNTAccount, '
                                                             'dbo.Employees.EmpWorkPhone, dbo.Employees.EmpEmail, '
                                                             'dbo.Employees.EmpBand FROM dbo.Employees '
                                                             'LEFT OUTER JOIN dbo.MachineOwner '
                                                             'ON '
                                                             'CAST(CAST(dbo.Employees.EmpId AS int) '
                                                             'AS varchar(10)) = dbo.MachineOwner.EmpId'):
                    yield device_raw, 'endpoint'
        except Exception:
            logger.exception(f'Problem with endoints')
        try:
            servers_connection.set_devices_paging(self.__devices_fetched_at_a_time)
            with servers_connection:
                for device_raw in servers_connection.query('select ServerName, OS, ManagedBy, [Owner Name], Role, '
                                                           'Country, IPAddress, [BusinessUnit], [divisionName], '
                                                           '[Account_name] from '
                                                           '[ServerInfo].[dbo].[vServersAllDetails]'):
                    yield device_raw, 'server'
        except Exception:
            logger.exception(f'Problem with servers')
        amd_ip_connection.set_devices_paging(self.__devices_fetched_at_a_time)
        with amd_ip_connection:
            for device_raw in amd_ip_connection.query('select * from vIP_Devices_Summary'):
                yield device_raw, 'amd_ip'

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'endpoint_db_address',
                    'title': 'Endpoints DB Address',
                    'type': 'string'
                },
                {
                    'name': 'endpoint_db_port',
                    'title': 'Endpoints DB Port',
                    'type': 'integer',
                    'default': 1433,
                    'format': 'port'
                },
                {
                    'name': 'endpoint_db_username',
                    'title': 'Endpoints DB Username',
                    'type': 'string'
                },                {
                    'name': 'endpoint_db_password',
                    'title': 'Endpoints DB Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'servers_db_address',
                    'title': 'Servers DB Address',
                    'type': 'string'
                },
                {
                    'name': 'servers_db_port',
                    'title': 'Servers DB Port',
                    'type': 'integer',
                    'default': 1433,
                    'format': 'port'
                },
                {
                    'name': 'servers_db_username',
                    'title': 'Servers DB Username',
                    'type': 'string'
                }, {
                    'name': 'servers_db_password',
                    'title': 'Servers DB Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'amd_ip_db_address',
                    'title': 'IP DB Address',
                    'type': 'string'
                },
                {
                    'name': 'amd_ip_db_port',
                    'title': 'IP DB Port',
                    'type': 'integer',
                    'default': 1433,
                    'format': 'port'
                },
                {
                    'name': 'amd_ip_db_username',
                    'title': 'IP DB Username',
                    'type': 'string'
                }, {
                    'name': 'amd_ip_db_password',
                    'title': 'IP DB Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'amd_ip_db_password',
                'amd_ip_db_username',
                'amd_ip_db_port',
                'amd_ip_db_address',
                'servers_db_password',
                'servers_db_username',
                'servers_db_port',
                'servers_db_address',
                'endpoint_db_password',
                'endpoint_db_username',
                'endpoint_db_port',
                'endpoint_db_address'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_type in devices_raw_data:
            if device_type == 'endpoint':
                try:
                    device = self._new_device_adapter()
                    device_id = device_raw.get('ComputerName')
                    if not device_id:
                        continue
                    device.id = 'endpoint_amd_' + '_' + device_raw.get('ComputerName')
                    device.hostname = device_raw.get('ComputerName')
                    device.email = device_raw.get('EmpEmail')
                    device.owner = (device_raw.get('EmpFirstName') or '') + ' ' + (device_raw.get('EmpLastName') or '')
                    device.set_raw({})
                    yield device
                except Exception:
                    logger.exception(f'Problem adding endpoint device: {str(device_raw)}')
            elif device_type == 'server':
                try:
                    device = self._new_device_adapter()
                    device_id = device_raw.get('ServerName')
                    if not device_id:
                        logger.warning(f'Bad device with no ID {device_id}')
                        continue
                    device.id = 'amd_server' + '_' + device_raw.get('ServerName')
                    device.hostname = device_raw.get('ServerName')
                    device.figure_os(device_raw.get('OS'))
                    device.owner = device_raw.get('Owner Name')
                    device.add_nic(ips=[device_raw.get('IPAddress')])
                    device.business_unit = device_raw.get('BusinessUnit')
                    device.division_name = device_raw.get('divisionName')
                    device.account_name = device_raw.get('Account_name')
                    device.country = device_raw.get('Country')
                    device.role = device_raw.get('Role')
                    device.device_managed_by = device_raw.get('ManagedBy')
                    device.set_raw(device_raw)
                    yield device
                except Exception:
                    logger.exception(f'Problem adding device: {str(device_raw)}')
            elif device_type == 'amd_ip':
                try:
                    device = self._new_device_adapter()
                    device_id = device_raw.get('DeviceID')
                    if not device_id:
                        logger.warning(f'Bad device with no ID {device_id}')
                        continue
                    device.id = 'amd_ip' + '_' + str(device_id) + '_' + device_raw.get('DeviceName')
                    device.add_nic(ips=[device_raw.get('IP')])
                    device.first_seen = parse_date(device_raw.get('DateAdded'))
                    device.hostname = device_raw.get('DeviceName')
                    device.figure_os((device_raw.get('OSPlatform') or '') + ' ' + (device_raw.get('Comment') or ''))
                    device.vlan_id = device_raw.get('VlanID')
                    device.owner = device_raw.get('AddedByFN')
                    device.region = device_raw.get('Region')
                    device.site_display_name = device_raw.get('SiteDisplayName')
                    device.device_status = device_raw.get('Status')
                    device.subnet_name = device_raw.get('SubnetName')
                    device.subnet_type = device_raw.get('SubnetType')
                    device.device_type = device_raw.get('DeviceType')
                    device.device_type_display_name = device_raw.get('DeviceTypeDisplayName')
                    device.set_raw(device_raw)
                    yield device
                except Exception:
                    logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'devices_fetched_at_a_time',
                    'type': 'integer',
                    'title': 'SQL pagination'
                }
            ],
            'required': ['devices_fetched_at_a_time'],
            'pretty_name': 'Asset Owner Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
