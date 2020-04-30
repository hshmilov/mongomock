import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import get_exception_string, is_domain_valid
from flexera_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class FlexeraAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        computer_system_status = Field(str, 'Computer System Status')
        computer_system_vm_name = Field(str, 'VM Name')
        computer_system_vm_id = Field(str, 'VM ID')
        computer_system_vm_type = Field(str, 'VM Type')
        computer_system_domain_role = Field(str, 'Domain Role')
        ad_distinguished_name = Field(str, 'AD Distinguished Name (DN)')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[consts.FLEXERA_HOST]

    def _test_reachability(self, client_config):
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port') or consts.DEFAULT_FLEXERA_PORT
        )

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(database=client_config.get(consts.FLEXERA_DATABASE),
                                         server=client_config[consts.FLEXERA_HOST],
                                         port=client_config.get(consts.FLEXERA_PORT, consts.DEFAULT_FLEXERA_PORT),
                                         devices_paging=self.__devices_fetched_at_a_time)
            connection.set_credentials(username=client_config[consts.USER],
                                       password=client_config[consts.PASSWORD])
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = f'Error connecting to client host: {client_config[consts.FLEXERA_HOST]}  ' \
                      f'database: ' \
                      f'{client_config.get(consts.FLEXERA_DATABASE)}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks, too-many-locals
    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            computers = dict()
            logger.info('Fetching from ComputerSystem...')
            for device_raw in client_data.query(f'select * from {consts.BASE_TABLE}'):
                if 'ComputerID' not in device_raw:
                    continue

                computers.setdefault(device_raw['ComputerID'], {})
                computers[device_raw['ComputerID']]['ComputerSystem'] = device_raw

            for table in consts.COMPUTER_SYSTEM_CORRELATION:
                logger.info(f'Fetching from {table}...')
                for device_raw in client_data.query(f'select * from {table}'):
                    if 'ComputerID' not in device_raw:
                        continue

                    if device_raw['ComputerID'] not in computers:
                        continue

                    computers[device_raw['ComputerID']].setdefault(table, [])
                    computers[device_raw['ComputerID']][table].append(device_raw)

            users = dict()
            for user_raw in client_data.query(consts.USER_QUERY):
                if 'UserID' not in user_raw:
                    continue

                users[user_raw['UserID']] = user_raw

            computer_resource_details = dict()
            for cud_raw in client_data.query(consts.COMPUTER_RESOURCE_DETAIL):
                if 'Name' not in cud_raw:
                    continue

                name = cud_raw.get('Name')
                serial = cud_raw.get('SerialNo') or ''

                computer_resource_details[f'{name}-{serial}'.upper()] = cud_raw

            logger.info(f'Devices: {len(computers.keys())}')
            for i, (computer_id, computer_data) in enumerate(computers.items()):
                try:
                    computer_usage = computer_data.get('ComputerUsage') or []
                    for usage in computer_usage:
                        if isinstance(usage, dict) and usage.get('UserID') and usage.get('UserID') in users:
                            computer_data.setdefault('Users', [])
                            computer_data['Users'].append(users[usage.get('UserID')])
                except Exception:
                    logger.exception(f'Problem appending users to computer')

                try:

                    name = computer_data['ComputerSystem']['HardwareName']
                    serial = ''
                    computer_bios = computer_data.get('ComputerBIOS')
                    if isinstance(computer_bios, list) and computer_bios:
                        serial = computer_bios[0].get('SerialNumber')

                    identifier = f'{name}-{serial}'.upper()
                    if identifier in computer_resource_details:
                        computer_data['ComputerResourceDetails'] = computer_resource_details[identifier]
                except Exception:
                    logger.exception(f'Problem getting detailed info')

                yield computer_data

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.FLEXERA_HOST,
                    'title': 'MSSQL Server',
                    'type': 'string'
                },
                {
                    'name': consts.FLEXERA_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_FLEXERA_PORT,
                    'format': 'port'
                },
                {
                    'name': consts.FLEXERA_DATABASE,
                    'title': 'Database',
                    'type': 'string',
                },
                {
                    'name': consts.USER,
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                consts.FLEXERA_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.FLEXERA_DATABASE
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self.create_device(device_raw, self._new_device_adapter())
            if device:
                yield device

    @staticmethod
    def create_device(device_raw, device: MyDeviceAdapter):
        try:
            # Initialize tables
            computer_system = device_raw.get('ComputerSystem') or {}
            computer_os = device_raw.get('ComputerOperatingSystem')
            computer_os = computer_os[0] \
                if isinstance(computer_os, list) and computer_os else {}
            computer_directory = device_raw.get('ComputerDirectory')
            computer_directory = computer_directory[0] \
                if isinstance(computer_directory, list) and computer_directory else {}
            computer_bios = device_raw.get('ComputerBIOS')
            computer_bios = computer_bios[0] \
                if isinstance(computer_bios, list) and computer_bios else {}
            disks = device_raw.get('LogicalDisk') or []
            nics = device_raw.get('NetworkAdapterConfiguration') or []
            users = device_raw.get('Users') or []
            computer_usage = device_raw.get('ComputerUsage') or []

            device_id = computer_system.get('ComputerID')
            if not device_id:
                logger.warning(f'Bad device with no ID {device_id}')
                return None

            # ComputerSystem
            device.id = str(device_id) + '_' + (computer_system.get('HardwareName') or '')
            device.hostname = computer_system.get('HardwareName')
            if is_domain_valid(computer_system.get('Domain')):
                device.domain = computer_system.get('Domain')
            device.device_manufacturer = computer_system.get('Manufacturer')
            device.device_model = computer_system.get('Model')
            try:
                device.total_number_of_physical_processors = computer_system.get('NumberOfProcessors')
                device.total_number_of_cores = computer_system.get('NumberOfLogicalProcessors')
            except Exception:
                pass
            try:
                if computer_system.get('TotalPhysicalMemory'):
                    device.total_physical_memory = computer_system.get('TotalPhysicalMemory') / (1024 ** 3)
            except Exception:
                pass

            device.computer_system_domain_role = computer_system.get('DomainRole')
            device.computer_system_status = computer_system.get('Status')
            device.computer_system_vm_id = computer_system.get('VMID')
            device.computer_system_vm_name = computer_system.get('VMName')
            device.computer_system_vm_type = computer_system.get('VMType')

            # Computer Operating System
            try:
                caption = computer_os.get('Caption')
                csdversion = computer_os.get('CSDVersion')
                version = computer_os.get('Version')
                device.figure_os((caption or '') + ' ' + (csdversion or '') + ' ' + (version or ''))
                if version:
                    device.os.build = str(version)
                if csdversion:
                    device.os.sp = str(csdversion)

                if computer_os.get('SerialNumber'):
                    device.os.serial = computer_os.get('SerialNumber')
            except Exception:
                pass

            try:
                device.device_serial = computer_bios.get('SerialNumber')
                device.bios_serial = computer_bios.get('SerialNumber')
                device.bios_manufacturer = computer_bios.get('Manufacturer')
            except Exception:
                pass

            try:
                if computer_os.get('FreePhysicalMemory'):
                    device.free_physical_memory = computer_os.get('FreePhysicalMemory') / (1024 ** 2)
            except Exception:
                pass

            # Domain
            device.ad_distinguished_name = computer_directory.get('ComputerDN')

            for disk in disks:
                try:
                    if not disk.get('Size'):
                        continue

                    if disk.get('DriveType') != 3:
                        # 3 == hd
                        continue

                    size = disk.get('Size') / (1024 ** 3) if isinstance(disk.get('Size'), int) else None
                    free_size = disk.get('FreeSpace') / (1024 ** 3) if isinstance(disk.get('FreeSpace'), int) else None

                    device.add_hd(
                        path=disk.get('HardwareName'),
                        device=disk.get('VolumeName'),
                        file_system=disk.get('FileSystem'),
                        total_size=size,
                        free_size=free_size,
                        description=disk.get('Description'),
                        serial_number=disk.get('VolumeSerialNumber')
                    )
                except Exception:
                    pass

            # Users

            try:
                time_by_user = {x['UserID']: x.get('LastReported') for x in computer_usage if x.get('UserID')}
            except Exception:
                time_by_user = {}
            for user in users:
                try:
                    user_id = user.get('UserID')
                    last_use_date = parse_date(time_by_user.get(user_id))
                    device.add_users(
                        user_sid=user_id,
                        username=user.get('UserCN') or user.get('SAMAccountName'),
                        last_use_date=last_use_date,
                    )
                except Exception:
                    pass

            # NIC's
            for nic in nics:
                try:
                    nic_caption = nic.get('Caption')
                    if not isinstance(nic_caption, str):
                        continue

                    if any(x in nic_caption.lower() for x in ['vmxnet', 'vmnet']):
                        continue

                    mac = nic.get('MACAddress')
                    ip = nic.get('IPAddress').split(',') if isinstance(nic.get('IPAddress'), str) else None

                    if mac or ip:
                        device.add_nic(
                            mac=mac,
                            ips=ip,
                            name=nic.get('Description') or nic_caption,
                            gateway=nic.get('DefaultIPGateway')
                        )
                except Exception:
                    pass

            device.last_seen = parse_date((device_raw.get('ComputerResourceDetails') or {}).get('LastUpdated'))

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

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
            'pretty_name': 'Flexera Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
