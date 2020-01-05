import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.users.user_adapter import UserAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from code42_adapter.connection import Code42Connection
from code42_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class BackupUsage(SmartJsonClass):
    alert_state = Field(int, 'Alert State')
    alert_states = ListField(str, 'Alert States')
    archive_bytes = Field(int, 'Archive Bytes')
    archive_format = Field(str, 'Archive Format')
    archive_guid = Field(str, 'Archive Guid')
    billable_bytes = Field(int, 'Billable Bytes')
    completion_rate_average = Field(int, 'Completion Rate Average')
    creation_date = Field(datetime.datetime, 'Creation Date')
    is_provider = Field(bool, 'Is Provider')
    last_backup = Field(datetime.datetime, 'Last Backup')
    last_compact_date = Field(datetime.datetime, 'Last Compact Date')
    last_completed_backup = Field(datetime.datetime, 'Last Completed Backup')
    last_connected = Field(datetime.datetime, 'Last Connected')
    last_maintenance_date = Field(datetime.datetime, 'Last Maintenance Date')
    modification_date = Field(datetime.datetime, 'Modification Date')
    percent_complete = Field(int, 'Percent Complete')
    selected_bytes = Field(int, 'Selected Bytes')
    selected_files = Field(int, 'Selected Files')
    send_rate_average = Field(int, 'Send Rate Average')
    server_guid = Field(str, 'Server Guid')
    server_host_name = Field(str, 'Server HostName')
    server_name = Field(str, 'Server Name')
    store_point_name = Field(str, 'Store Point Name')
    target_computer_name = Field(str, 'Target Computer Name')
    target_computer_type = Field(str, 'Target Computer Type')
    todo_bytes = Field(int, 'Todo Bytes')
    todo_files = Field(int, 'Todo Files')
    using = Field(bool, 'Using')


class Code42Adapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        product_version = Field(str, 'Product Version')
        device_service = Field(str, 'Device Service')
        java_version = Field(str, 'Java Version')
        device_status = Field(str, 'Device Status')
        device_type = Field(str, 'Device Type')
        user_id = Field(str, 'User ID')
        address = Field(str, 'Address')
        remote_address = Field(str, 'Remote Address')
        active_state = Field(bool, 'Active State')
        login_date = Field(datetime.datetime, 'Login Date')
        backup_usages = ListField(BackupUsage, 'Backup Usages')

    class MyUserAdapter(UserAdapter):
        uid = Field(str, 'UID')
        licenses = ListField(str, 'Licenses')
        organization_name = Field(str, 'Organization Name')
        user_active = Field(bool, 'User Active')
        invited = Field(bool, 'Invited')
        blocked = Field(bool, 'Blocked')
        password_reset = Field(bool, 'Password Reset')
        org_type = Field(str, 'Organization Type')
        notes = ListField(str, 'Notes')
        modification_date = Field(datetime.datetime, 'Modification Date')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'))

    @staticmethod
    def _connect_client(client_config):
        try:
            with Code42Connection(domain=client_config['domain'],
                                  verify_ssl=client_config['verify_ssl'],
                                  username=client_config['username'],
                                  password=client_config['password'],
                                  https_proxy=client_config.get('https_proxy')) as connection:
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
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema Code42Adapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Code42 Domain',
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

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device_id = device_raw.get('guid')
                if not device_id:
                    logger.warning(f'Bad device with no guid {device_raw}')
                    continue
                device.id = device_id + '_' + (device_raw.get('name') or '')
                device.hostname = device_raw.get('name')
                try:
                    device.last_seen = parse_date(device_raw.get('lastConnected'))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
                try:
                    device.figure_os((device_raw.get('osName') or '') + ' ' + (device_raw.get('osVersion') or ''))
                except Exception:
                    logger.exception(f'Problem getting os for {device_raw}')
                device.product_version = device_raw.get('productVersion')
                device.device_service = device_raw.get('service')
                device.java_version = device_raw.get('javaVersion')
                agent_version = str(device_raw.get('version')) if device_raw.get('version') else None
                device.add_agent_version(agent=AGENT_NAMES.code42, version=agent_version)
                device.device_status = device_raw.get('status')
                device.device_type = device_raw.get('type')
                device.login_date = parse_date(device_raw.get('loginDate'))
                device.user_id = str(device_raw.get('userId')) if device_raw.get('userId') else None
                device.address = device_raw.get('address')
                device.remote_address = device_raw.get('remoteAddress')
                device.active_state = device_raw.get('active')
                try:
                    backup_usages_raw = device_raw.get('backupUsage')
                    if not isinstance(backup_usages_raw, list):
                        backup_usages_raw = []
                    for backup_usage_raw in backup_usages_raw:
                        try:
                            alert_state = backup_usage_raw.get('alertState') \
                                if isinstance(backup_usage_raw.get('alertState'), int) else None
                            alert_states = backup_usage_raw.get('alertStates') \
                                if isinstance(backup_usage_raw.get('alertStates'), list) else None
                            archive_bytes = backup_usage_raw.get('archiveBytes') \
                                if isinstance(backup_usage_raw.get('archiveBytes'), int) else None
                            billable_bytes = backup_usage_raw.get('billableBytes') \
                                if isinstance(backup_usage_raw.get('billableBytes'), int) else None
                            completion_rate_average = backup_usage_raw.get('completionRateAverage') \
                                if isinstance(backup_usage_raw.get('completionRateAverage'), int) else None
                            is_provider = backup_usage_raw.get('isProvider') \
                                if isinstance(backup_usage_raw.get('isProvider'), bool) else None
                            percent_complete = backup_usage_raw.get('percentComplete') \
                                if isinstance(backup_usage_raw.get('percentComplete'), int) else None
                            selected_bytes = backup_usage_raw.get('selectedBytes') \
                                if isinstance(backup_usage_raw.get('selectedBytes'), int) else None
                            selected_files = backup_usage_raw.get('selectedFiles') \
                                if isinstance(backup_usage_raw.get('selectedFiles'), int) else None
                            send_rate_average = backup_usage_raw.get('sendRateAverage') \
                                if isinstance(backup_usage_raw.get('sendRateAverage'), int) else None
                            using = backup_usage_raw.get('using') \
                                if isinstance(backup_usage_raw.get('using'), bool) else None
                            todo_bytes = backup_usage_raw.get('todoBytes') \
                                if isinstance(backup_usage_raw.get('todoBytes'), int) else None
                            todo_files = backup_usage_raw.get('todoFiles') \
                                if isinstance(backup_usage_raw.get('todoFiles'), int) else None

                            backup_usage = BackupUsage(alert_state=alert_state,
                                                       alert_states=alert_states,
                                                       archive_bytes=archive_bytes,
                                                       archive_format=backup_usage_raw.get('archiveFormat'),
                                                       archive_guid=backup_usage_raw.get('archiveGuid'),
                                                       billable_bytes=billable_bytes,
                                                       completion_rate_average=completion_rate_average,
                                                       creation_date=parse_date(backup_usage_raw.get('creationDate')),
                                                       is_provider=is_provider,
                                                       last_backup=parse_date(backup_usage_raw.get('lastBackup')),
                                                       last_compact_date=parse_date(
                                                           backup_usage_raw.get('lastCompactDate')),
                                                       last_completed_backup=parse_date(
                                                           backup_usage_raw.get('lastCompletedBackup')),
                                                       last_connected=parse_date(
                                                           backup_usage_raw.get('lastConnected')),
                                                       last_maintenance_date=parse_date(
                                                           backup_usage_raw.get('lastMaintenanceDate')),
                                                       modification_date=parse_date(
                                                           backup_usage_raw.get('modificationDate')),
                                                       percent_complete=percent_complete,
                                                       selected_bytes=selected_bytes,
                                                       selected_files=selected_files,
                                                       send_rate_average=send_rate_average,
                                                       server_guid=backup_usage_raw.get('serverGuid'),
                                                       server_host_name=backup_usage_raw.get('serverHostName'),
                                                       server_name=backup_usage_raw.get('serverName'),
                                                       store_point_name=backup_usage_raw.get('storePointName'),
                                                       target_computer_name=backup_usage_raw.get('targetComputerName'),
                                                       target_computer_type=backup_usage_raw.get('targetComputerType'),
                                                       todo_bytes=todo_bytes,
                                                       todo_files=todo_files,
                                                       using=using)
                            device.backup_usages.append(backup_usage)
                        except Exception:
                            logger.exception(f'Problem with backup usage for {device_raw}')
                except Exception:
                    logger.exception(f'Problem with backup usages for {device_raw}')
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem with fetching Code42 Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]

    # pylint: disable=arguments-differ

    @staticmethod
    def _query_users_by_client(key, data):
        with data:
            yield from data.get_user_list()

    def _create_user(self, user_raw):
        try:
            user = self._new_user_adapter()
            user_id = user_raw.get('userId')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('username') or '')
            user.uid = user_raw.get('userUid')
            user.username = user_raw.get('username')
            user.mail = user_raw.get('email')
            user.user_status = user_raw.get('status')
            user.first_name = user_raw.get('firstName')
            user.last_name = user_raw.get('lastName')
            user.password_reset = user_raw.get('passwordReset') \
                if isinstance(user_raw.get('passwordReset'), bool) else None
            user.invited = user_raw.get('invited') if isinstance(user_raw.get('invited'), bool) else None
            user.blocked = user_raw.get('blocked') if isinstance(user_raw.get('blocked'), bool) else None
            user.licenses = user_raw.get('licenses') if isinstance(user_raw.get('licenses'), list) else None
            user.organization_name = user_raw.get('orgName')
            user.user_created = parse_date(user_raw.get('creationDate'))
            user.user_status = user_raw.get('status')
            user.org_type = user_raw.get('orgType')
            if isinstance(user_raw.get('notes'), list) and user_raw.get('notes'):
                user.notes = user_raw.get('notes')
            if isinstance(user_raw.get('notes'), str) and user_raw.get('notes'):
                user.notes = user_raw.get('notes').split(',')
            user.modification_date = parse_date(user_raw.get('modificationDate'))
            user.user_active = user_raw.get('active') if isinstance(user_raw.get('active'), bool) else None
            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching BambooHR user for {user_raw}')
            return None

    def _parse_users_raw_data(self, users_raw_data):
        for user_raw in users_raw_data:
            user = self._create_user(user_raw)
            if user:
                yield user
