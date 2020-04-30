import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.mssql.connection import MSSQLConnection
from axonius.fields import Field, ListField
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.devices.device_adapter import RegistryInfomation
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.utils.network.sockets import test_reachability_tcp
from axonius.utils.parsing import get_exception_string, is_domain_valid
from lansweeper_adapter import consts
from lansweeper_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class LansweeprError(SmartJsonClass):
    error_type = Field(str, 'Error Type')
    error_text = Field(str, 'Error Text')


class LansweeperAdapter(AdapterBase, Configurable):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        last_active_scan = Field(datetime.datetime, 'Last Active Scan')
        lsat_ls_agent = Field(datetime.datetime, 'Last Ls Agent')
        lansweeper_type = Field(str, 'Lansweeper Type')
        errors_data = ListField(LansweeprError, 'Errors Data')
        last_triggered = Field(datetime.datetime, 'Last Triggered')
        last_scan_fallback = Field(datetime.datetime, 'Last Scan Fallback')
        last_performance_scan = Field(datetime.datetime, 'Last Performance Scan')
        state_name = Field(str, 'State Name')
        device_version = Field(str, 'Device version')

        def add_registry_information(self, **kwargs):
            self.registry_information.append(RegistryInfomation(**kwargs))

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return test_reachability_tcp(
            client_config.get('server'),
            client_config.get('port') or consts.DEFAULT_LANSWEEPER_PORT
        )

    def _connect_client(self, client_config):
        try:
            connection = MSSQLConnection(
                database=client_config.get(consts.LANSWEEPER_DATABASE),
                server=client_config[consts.LANSWEEPER_HOST],
                port=client_config.get(consts.LANSWEEPER_PORT, consts.DEFAULT_LANSWEEPER_PORT),
                devices_paging=self.__devices_fetched_at_a_time,
            )
            connection.set_credentials(
                username=client_config[consts.USER], password=client_config[consts.PASSWORD]
            )
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as err:
            message = (
                f'Error connecting to client host: {client_config[consts.LANSWEEPER_HOST]}  '
                f'database: '
                f'{client_config.get(consts.LANSWEEPER_DATABASE)}'
            )
            logger.exception(message)
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _query_devices_by_client(self, client_name, client_data):
        client_data.set_devices_paging(self.__devices_fetched_at_a_time)
        with client_data:
            processor_dict = dict()
            try:
                for processor_data in client_data.query(consts.PROCESSOR_QUERY):
                    asset_id = processor_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in processor_dict:
                        processor_dict[asset_id] = []
                    processor_dict[asset_id].append(processor_data)
            except Exception:
                logger.exception(f'Problem getting state names')

            state_name_dict = dict()
            try:
                for state_name_data in client_data.query(consts.STATE_NAMES_QUERY):
                    state_id = state_name_data.get('State')
                    state_name = state_name_data.get('Statename')
                    if not state_id or not state_name:
                        continue
                    state_name_dict[state_id] = state_name
            except Exception:
                logger.exception(f'Problem getting state names')

            custom_data_dict = dict()
            try:
                for custom_data in client_data.query(consts.CUSTOM_DATA_QUERY):
                    asset_id = custom_data.get('AssetID')
                    if not asset_id:
                        continue
                    custom_data_dict[asset_id] = custom_data
            except Exception:
                logger.exception(f'Problem getting custom data')

            errors_dict = dict()
            try:
                for errors_data in client_data.query(consts.ERRORS_QUERY):
                    asset_id = errors_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in errors_dict:
                        errors_dict[asset_id] = []
                    errors_dict[asset_id].append(errors_data)
            except Exception:
                logger.exception(f'Problem getting errors')

            encryption_dict = dict()
            try:
                for encryption_data in client_data.query(consts.ENCRYPTION_QUERY):
                    asset_id = encryption_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in encryption_dict:
                        encryption_dict[asset_id] = []
                    encryption_dict[asset_id].append(encryption_data)
            except Exception:
                logger.exception(f'Problem getting encryption')
            disks_dict = dict()
            try:
                for disks_data in client_data.query(consts.DISKS_QUERY):
                    asset_id = disks_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in disks_dict:
                        disks_dict[asset_id] = []
                    disks_dict[asset_id].append(disks_data)
            except Exception:
                logger.exception(f'Problem getting disks')

            users_groups_dict = dict()
            try:
                for users_groups_data in client_data.query(consts.USERS_GROUPS_QUERY):
                    asset_id = users_groups_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in users_groups_dict:
                        users_groups_dict[asset_id] = []
                    users_groups_dict[asset_id].append(users_groups_data)
            except Exception:
                logger.exception(f'Problem getting users groups')

            asset_processes_dict = dict()
            try:
                for asset_processes_data in client_data.query(consts.PROCESSES_QUERY):
                    asset_id = asset_processes_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_processes_dict:
                        asset_processes_dict[asset_id] = []
                    asset_processes_dict[asset_id].append(asset_processes_data)
            except Exception:
                logger.exception(f'Problem getting query processes')

            autoruns_id_to_autoruns_data_dict = dict()
            try:
                for autoruns_data in client_data.query(consts.QUERY_AUTORUNS_3):
                    autoruns_id_to_autoruns_data_dict[autoruns_data.get('AutorunUNI')] = autoruns_data
            except Exception:
                logger.warning(f'Problem getting query autoruns 3', exc_info=True)

            autoruns_id_to_autoruns_loc_dict = dict()
            try:
                for autoruns_loc in client_data.query(consts.QUERY_AUTORUNS_2):
                    autoruns_id_to_autoruns_loc_dict[autoruns_loc.get('LocationID')] = autoruns_loc
            except Exception:
                logger.warning(f'Problem getting query autoruns 2', exc_info=True)

            asset_autoruns_dict = dict()
            try:
                for asset_autoruns_data in client_data.query(consts.QUERY_AUTORUNS):
                    asset_id = asset_autoruns_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_autoruns_dict:
                        asset_autoruns_dict[asset_id] = []
                    asset_autoruns_dict[asset_id].append(asset_autoruns_data)
            except Exception:
                logger.exception(f'Problem getting query autoruns')

            bios_data_dict = dict()
            try:
                for bios_data in client_data.query(consts.BIOS_QUERY):
                    bios_data_dict[bios_data.get('AssetID')] = bios_data
            except Exception:
                logger.exception(f'Problem getting bios data')

            soft_id_to_soft_data_dict = dict()
            try:
                for soft_data in client_data.query(consts.QUERY_SOFTWARE_2):
                    soft_id_to_soft_data_dict[soft_data.get('SoftID')] = soft_data
            except Exception:
                logger.exception(f'Problem getting query software 2')
            asset_software_dict = dict()
            try:
                for asset_soft_data in client_data.query(consts.QUERY_SOFTWARE):
                    asset_id = asset_soft_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_software_dict:
                        asset_software_dict[asset_id] = []
                    asset_software_dict[asset_id].append(asset_soft_data)
            except Exception:
                logger.exception(f'Problem getting query software')

            asset_software_linux_dict = dict()
            try:
                for asset_soft_data in client_data.query(consts.QUERY_LINUX_SOFTWARE):
                    asset_id = asset_soft_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_software_linux_dict:
                        asset_software_linux_dict[asset_id] = []
                    asset_software_linux_dict[asset_id].append(asset_soft_data)
            except Exception:
                logger.exception(f'Problem getting query software')

            hotfix_id_to_hotfix_data_dict = dict()
            try:
                for hotfix_data in client_data.query(consts.QUERY_HOTFIX_2):
                    hotfix_id_to_hotfix_data_dict[hotfix_data.get('QFEID')] = hotfix_data
            except Exception:
                logger.exception(f'Problem getting query hotfix 2')
            asset_hotfix_dict = dict()
            try:
                for asset_hotfix_data in client_data.query(consts.QUERY_HOTFIX):
                    asset_id = asset_hotfix_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_hotfix_dict:
                        asset_hotfix_dict[asset_id] = []
                    asset_hotfix_dict[asset_id].append(asset_hotfix_data)
            except Exception:
                logger.exception(f'Problem getting query hotfix')

            asset_reg_dict = dict()
            try:
                for asset_reg_data in client_data.query(consts.QUERY_REGISTRY):
                    asset_id = asset_reg_data.get('AssetID')
                    if not asset_id:
                        continue
                    if asset_id not in asset_reg_dict:
                        asset_reg_dict[asset_id] = []
                    asset_reg_dict[asset_id].append(asset_reg_data)
            except Exception:
                logger.exception(f'Problem getting query software')

            for device_raw in client_data.query(consts.LANSWEEPER_QUERY_DEVICES):
                yield (device_raw,
                       asset_software_dict,
                       soft_id_to_soft_data_dict,
                       asset_hotfix_dict,
                       hotfix_id_to_hotfix_data_dict,
                       asset_reg_dict, bios_data_dict,
                       asset_autoruns_dict, autoruns_id_to_autoruns_data_dict, autoruns_id_to_autoruns_loc_dict,
                       asset_processes_dict, users_groups_dict, disks_dict, encryption_dict, errors_dict,
                       custom_data_dict, state_name_dict, asset_software_linux_dict, processor_dict)

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {'name': consts.LANSWEEPER_HOST, 'title': 'MSSQL Server', 'type': 'string'},
                {
                    'name': consts.LANSWEEPER_PORT,
                    'title': 'Port',
                    'type': 'integer',
                    'default': consts.DEFAULT_LANSWEEPER_PORT,
                    'format': 'port',
                },
                {'name': consts.LANSWEEPER_DATABASE, 'title': 'Database', 'type': 'string'},
                {'name': consts.USER, 'title': 'User Name', 'type': 'string'},
                {
                    'name': consts.PASSWORD,
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password',
                },
            ],
            'required': [
                consts.LANSWEEPER_HOST,
                consts.USER,
                consts.PASSWORD,
                consts.LANSWEEPER_DATABASE,
            ],
            'type': 'array',
        }

    # pylint: disable=R0912,R0915,R0914
    def _parse_raw_data(self, devices_raw_data):
        # pylint: disable=R1702
        for (
                device_raw,
                asset_software_dict,
                soft_id_to_soft_data_dict,
                asset_hotfix_dict,
                hotfix_id_to_hotfix_data_dict,
                asset_reg_dict,
                bios_data_dict,
                asset_autoruns_dict,
                autoruns_id_to_autoruns_data_dict,
                autoruns_id_to_autoruns_loc_dict,
                asset_processes_dict,
                users_groups_dict,
                disks_dict,
                encryption_dict,
                errors_dict, custom_data_dict, state_name_dict, asset_software_linux_dict, processor_dict
        ) in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('AssetUnique')
                if not device_id:
                    logger.error(f'Found a device with no id: {device_raw}, skipping')
                    continue
                device.id = device_id + '_' + (device_raw.get('FQDN') or '')
                try:
                    custom_data = custom_data_dict.get(device_raw.get('AssetID'))
                    if isinstance(custom_data, dict):
                        state_id = custom_data.get('State')
                        if state_id:
                            device.state_name = state_name_dict.get(state_id)
                        device.device_model = custom_data.get('Model')
                        device.device_manufacturer = custom_data.get('Manufacturer')
                except Exception:
                    logger.exception(f'Problem getting custom data')

                try:
                    processors_data = processor_dict.get(device_raw.get('AssetID'))
                    if isinstance(processors_data, list):
                        for processor_data in processors_data:
                            device.add_cpu(manufacturer=processor_data.get('Manufacturer'),
                                           name=processor_data.get('Caption'),
                                           cores=processor_data.get('NumberOfCores')
                                           if isinstance(processor_data.get('NumberOfCores'), int) else None,
                                           family=consts.CPU_FAMILY_DICT.get(processor_data.get('Family')))
                except Exception:
                    logger.exception(f'Problem parsing bios data for {device_raw}')

                try:
                    bios_data = bios_data_dict.get(device_raw.get('AssetID'))
                    if bios_data:
                        device.bios_serial = bios_data.get('SerialNumber')
                        device.bios_version = bios_data.get('Version')
                except Exception:
                    logger.exception(f'Problem parsing bios data for {device_raw}')
                try:
                    disks_data = disks_dict.get(device_raw.get('AssetID'))
                    encryption_data = encryption_dict.get(device_raw.get('AssetID'))
                    if not encryption_data:
                        encryption_data = []
                    if not isinstance(disks_data, list):
                        disks_data = []
                    for disk_data in disks_data:
                        try:
                            total_size = disk_data.get('Size')
                            try:
                                total_size = int(total_size)
                                total_size = total_size / (1024.0 ** 3)
                            except Exception:
                                total_size = None
                            free_size = disk_data.get('Freespace')
                            try:
                                free_size = int(free_size)
                                free_size = free_size / (1024.0 ** 3)
                            except Exception:
                                free_size = None
                            is_encrypted = None
                            path = disk_data.get('Caption')
                            try:
                                for disk_encryption_data in encryption_data:
                                    try:
                                        if isinstance(disk_encryption_data, dict) \
                                                and disk_encryption_data.get('DriveLetter') == path:
                                            if int(disk_encryption_data.get('ProtectionStatus')) == 0:
                                                is_encrypted = False
                                            if int(disk_encryption_data.get('ProtectionStatus')) == 1:
                                                is_encrypted = True
                                    except Exception:
                                        pass
                            except Exception:
                                logger.exception(f'Problem with encryption for {encryption_data}')
                            device.add_hd(device=disk_data.get('Description'),
                                          path=path,
                                          total_size=total_size,
                                          is_encrypted=is_encrypted,
                                          free_size=free_size)
                        except Exception:
                            logger.exception(f'Problem with disks')
                except Exception:
                    logger.exception(f'Problem with users groups for {device_raw}')

                try:
                    errors_data = errors_dict.get(device_raw.get('AssetID'))
                    if not isinstance(errors_data, list):
                        errors_data = []
                    for error_data in errors_data:
                        try:
                            error_type = consts.ERRORS_TYPES.get(int(error_data.get('ErrorType')))
                            if not error_type:
                                continue
                            error_text = error_data.get('ErrorText')
                            device.errors_data.append(LansweeprError(error_text=error_text,
                                                                     error_type=error_type))
                        except Exception:
                            logger.exception(f'Problem with error data {error_data}')
                except Exception:
                    logger.exception(f'Problem with errors data')
                try:
                    users_groups_data = users_groups_dict.get(device_raw.get('AssetID'))
                    if not isinstance(users_groups_data, list):
                        users_groups_data = []
                    for user_groups_data in users_groups_data:
                        try:
                            if user_groups_data and user_groups_data.get('Admingroup') is True:
                                admin_name = (user_groups_data.get('Username') or '') +\
                                    '@' + (user_groups_data.get('Domainname') or '')
                                device.add_local_admin(admin_type='Admin User',
                                                       admin_name=admin_name)
                        except Exception:
                            logger.exception(f'Problem with users groups data {user_groups_data}')
                except Exception:
                    logger.exception(f'Problem with users groups for {device_raw}')
                try:
                    asset_processes_list = asset_processes_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_processes_list, list):
                        for process_data in asset_processes_list:
                            device.add_process(name=process_data.get('ExecutablePath'))
                except Exception:
                    logger.exception(f'Problem getting processes data for {device_raw}')
                try:
                    asset_software_list = asset_software_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_software_list, list):
                        for asset_software in asset_software_list:
                            if asset_software.get('softID'):
                                software_data = soft_id_to_soft_data_dict.get(
                                    asset_software.get('softID')
                                )
                                if software_data:
                                    device.add_installed_software(
                                        name=software_data.get('softwareName'),
                                        vendor=software_data.get('SoftwarePublisher'),
                                        version=asset_software.get('softwareVersion'),
                                    )
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')
                try:
                    asset_software_list = asset_software_linux_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_software_list, list):
                        for asset_software in asset_software_list:
                            if asset_software.get('SoftwareUniID'):
                                software_data = soft_id_to_soft_data_dict.get(
                                    asset_software.get('SoftwareUniID')
                                )
                                if software_data:
                                    device.add_installed_software(
                                        name=software_data.get('softwareName'),
                                        vendor=software_data.get('SoftwarePublisher'),
                                        version=asset_software.get('Version'),
                                    )
                except Exception:
                    logger.exception(f'Problem adding software to {device_raw}')
                try:
                    asset_autoruns_list = asset_autoruns_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_autoruns_list, list):
                        for asset_autorun in asset_autoruns_list:
                            autorun_caption = None
                            autorun_command = None
                            autorun_location = None
                            autorun_uni_id = asset_autorun.get('AutorunUNI')
                            autorun_loc_id = asset_autorun.get('LocationID')
                            if autorun_uni_id and autoruns_id_to_autoruns_data_dict.get(autorun_uni_id):
                                autorun_caption = autoruns_id_to_autoruns_data_dict.get(autorun_uni_id).get('Caption')
                                autorun_command = autoruns_id_to_autoruns_data_dict.get(autorun_uni_id).get('Command')
                            if autorun_loc_id and autoruns_id_to_autoruns_loc_dict.get(autorun_loc_id):
                                autorun_location = autoruns_id_to_autoruns_loc_dict.get(autorun_loc_id).get('Location')
                            device.add_autorun_data(autorun_location=autorun_location,
                                                    autorun_caption=autorun_caption,
                                                    autorun_command=autorun_command)
                except Exception:
                    logger.exception(f'Problem adding autoruns to {device_raw}')

                try:
                    asset_hotfix_list = asset_hotfix_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_hotfix_list, list):
                        for asset_hotfix in asset_hotfix_list:
                            if asset_hotfix.get('QFEID'):
                                hotfix_data = hotfix_id_to_hotfix_data_dict.get(
                                    asset_hotfix.get('QFEID')
                                )
                                if hotfix_data:
                                    patch_description = hotfix_data.get('Description') or ''
                                    if hotfix_data.get('FixComments'):
                                        patch_description += ' Hotfix Comments:' + hotfix_data.get(
                                            'FixComments'
                                        )
                                    if not patch_description:
                                        patch_description = None
                                    installed_on = None
                                    try:
                                        installed_on = parse_date(asset_hotfix.get('InstalledOn'))
                                    except Exception:
                                        logger.exception(
                                            f'Problem getting installed on for patch {asset_hotfix}'
                                        )
                                    device.add_security_patch(
                                        security_patch_id=hotfix_data.get('HotFixID'),
                                        installed_on=installed_on,
                                        patch_description=patch_description,
                                    )
                except Exception:
                    logger.exception(f'Problem adding patch to {device_raw}')
                domain = device_raw.get('Domain')
                if is_domain_valid(domain):
                    device.domain = domain
                    device.part_of_domain = True
                else:
                    device.part_of_domain = False
                device.hostname = device_raw.get('FQDN')
                device.device_version = device_raw.get('Version')
                device.name = device_raw.get('AssetName')
                try:
                    mac = device_raw.get('Mac') if device_raw.get('Mac') else None
                    if self.__drop_no_mac_addresses_device and not mac:
                        continue
                    ips = [device_raw.get('IPAddress')] if device_raw.get('IPAddress') else None
                    if mac or ips:
                        device.add_nic(mac, ips)
                except Exception:
                    logger.exception(f'Problem adding NIC to {device_raw}')
                try:
                    if device_raw.get('Uptime'):
                        try:
                            device.set_boot_time(
                                uptime=datetime.timedelta(seconds=int(device_raw.get('Uptime')))
                            )
                        except Exception:
                            logger.exception('uptime failed')
                except Exception:
                    logger.exception(f'Problem adding boot time to {device_raw}')
                device.last_seen = parse_date(device_raw.get('Lastseen'))
                try:
                    device.total_physical_memory = (
                        device_raw.get('Memory') / 1024 if device_raw.get('Memory') else None
                    )
                except Exception:
                    logger.exception(f'Problem getting memory for {device_raw}')
                device.add_agent_version(agent=AGENT_NAMES.lansweeper, version=device_raw.get('LsAgentVersion'))
                username = device_raw.get('Username')
                user_domain = device_raw.get('Userdomain')
                if username:
                    if is_domain_valid(user_domain):
                        device.last_used_users = [f'{user_domain}\\{username}']
                    else:
                        device.last_used_users = [username]
                device.description = device_raw.get('Description')
                try:
                    device.last_active_scan = parse_date(device_raw.get('LastActiveScan'))
                except Exception:
                    logger.exception(f'Problem getting last active scan for {device_raw}')
                try:
                    device.lsat_ls_agent = parse_date(device_raw.get('LastLsAgent'))
                except Exception:
                    logger.exception(f'Problem getting last ls agent for {device_raw}')
                device.last_triggered = parse_date(device_raw.get('Lasttriggered'))
                device.last_scan_fallback = parse_date(device_raw.get('LastLsFallBack'))
                device.last_performance_scan = device_raw.get('LastPerformanceScan')
                try:
                    asset_reg_list = asset_reg_dict.get(device_raw.get('AssetID'))
                    if isinstance(asset_reg_list, list):
                        for asset_reg_data in asset_reg_list:
                            try:
                                reg_key = asset_reg_data.get('Regkey')
                                value_name = asset_reg_data.get('Valuename')
                                value_data = asset_reg_data.get('Value')
                                last_changed = None
                                try:
                                    last_changed = parse_date(asset_reg_data.get('Lastchanged'))
                                except Exception:
                                    logger.exception(
                                        f'Problem getting last_changed for {asset_reg_data}'
                                    )
                                device.add_registry_information(
                                    reg_key=reg_key,
                                    value_name=value_name,
                                    value_data=value_data,
                                    last_changed=last_changed,
                                )
                            except Exception:
                                logger.exception(f'Problem getting asset reg data {asset_reg_data}')
                except Exception:
                    logger.exception(f'Problem getting reg informaation for {device_raw}')
                try:
                    if device_raw.get('Assettype') is not None:
                        lansweeper_type = consts.LANSWEEPER_TYPE_DICT.get(
                            str(device_raw.get('Assettype'))
                        )
                        if lansweeper_type in consts.BAD_TYPES:
                            continue
                        device.lansweeper_type = lansweeper_type
                except Exception:
                    logger.exception(f'Problem adding type')
                raw_dict = dict()
                for key in device_raw:
                    raw_dict[key] = str(device_raw[key])
                device.set_raw(raw_dict)
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
                },
                {
                    'name': 'drop_no_mac_addresses_device',
                    'type': 'bool',
                    'title': 'Do not fetch devices with mo MAC address'
                }
            ],
            'required': ['drop_no_mac_addresses_device'],
            'pretty_name': 'Lansweeper Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000,
            'drop_no_mac_addresses_device': False
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
        self.__drop_no_mac_addresses_device = config['drop_no_mac_addresses_device']
