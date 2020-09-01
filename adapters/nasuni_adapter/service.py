import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.nasuni.connection import NasuniConnection
from axonius.clients.nasuni.consts import SECONDS_TO_DAY
from axonius.utils.datetime import parse_date
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none, float_or_none
from nasuni_adapter.client_id import get_client_id
from nasuni_adapter.structures import NasuniDeviceInstance, NasuniAlertSettings, Cache, RemoteSupport, Updates, SNMP, \
    CIFS

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class NasuniAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(NasuniDeviceInstance):
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
        connection = NasuniConnection(domain=client_config.get('domain'),
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
        The schema NasuniAdapter expects from configs

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

    # pylint: disable=too-many-statements, too-many-locals
    @staticmethod
    def _fill_nasuni_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.version = device_raw.get('build')
            device.management_state = device_raw.get('management_state')

            settings = device_raw.get('settings')
            if isinstance(settings, dict):
                alert_thresholds = settings.get('alert_thresholds')
                if isinstance(alert_thresholds, dict):
                    cpu_alert_settings_raw = alert_thresholds.get('cpu_alert_settings')
                    if isinstance(cpu_alert_settings_raw, dict):
                        cpu_alert_settings = NasuniAlertSettings()
                        cpu_alert_settings.enabled = parse_bool_from_raw(cpu_alert_settings_raw.get('cpu_enabled'))
                        cpu_alert_settings.threshold = int_or_none(cpu_alert_settings_raw.get('cpu_threshold'))
                        cpu_alert_settings.duration = int_or_none(cpu_alert_settings_raw.get('cpu_duration'))
                        device.cpu_alert_settings = cpu_alert_settings

                    memory_alert_settings_raw = alert_thresholds.get('memory_alert_settings')
                    if isinstance(memory_alert_settings_raw, dict):
                        memory_alert_settings = NasuniAlertSettings()
                        memory_alert_settings.enabled = parse_bool_from_raw(
                            memory_alert_settings_raw.get('memory_enabled'))
                        memory_alert_settings.threshold = int_or_none(memory_alert_settings_raw.get('memory_threshold'))
                        memory_alert_settings.duration = int_or_none(memory_alert_settings_raw.get('memory_duration'))
                        device.memory_alert_settings = memory_alert_settings

                    snap_shot_alert_settings_raw = alert_thresholds.get('snapshot_alert_settings')
                    if isinstance(snap_shot_alert_settings_raw, dict):
                        snap_shot_alert_settings = NasuniAlertSettings()
                        snap_shot_alert_settings.enabled = parse_bool_from_raw(
                            snap_shot_alert_settings_raw.get('snapshot_enabled'))
                        snap_shot_alert_settings.duration = int_or_none(
                            snap_shot_alert_settings_raw.get('snapshot_duration'))
                        device.snap_shot_alert_settings = snap_shot_alert_settings

                cached_reserved = settings.get('cache_reserved')
                if isinstance(cached_reserved, dict):
                    cache_reserved = Cache()
                    cache_reserved.reserved = cached_reserved.get('reserved')
                    cache_reserved.cache_max = int_or_none(cached_reserved.get('maxv'))
                    cache_reserved.cache_min = int_or_none(cached_reserved.get('minv'))
                    device.cache_reserved = cache_reserved

                remote_support_raw = settings.get('remote_support')
                if isinstance(remote_support_raw, dict):
                    remote_support = RemoteSupport()
                    remote_support.connected = parse_bool_from_raw(remote_support_raw.get('connected'))
                    remote_support.enabled = parse_bool_from_raw(remote_support_raw.get('enabled'))
                    remote_support.running = parse_bool_from_raw(remote_support_raw.get('running'))
                    remote_support.timeout = int_or_none(remote_support_raw.get('timeout'))
                    device.remote_support = remote_support

                updates_raw = settings.get('updates')
                if isinstance(updates_raw, dict):
                    updates = Updates()
                    updates.available = parse_bool_from_raw(updates_raw.get('updates_available'))
                    updates.current_version = updates_raw.get('current_version')
                    updates.new_version = updates_raw.get('new_version')
                    device.updates = updates

                snmp_raw = settings.get('snmp')
                if isinstance(snmp_raw, dict):
                    snmp = SNMP()
                    snmp.v2_enabled = parse_bool_from_raw(snmp_raw.get('v2_enabled'))
                    snmp.v2_community = snmp_raw.get('v2_community')
                    snmp.v3_enabled = parse_bool_from_raw(snmp_raw.get('v3_enabled'))
                    snmp.v3_username = snmp_raw.get('v3_username')
                    snmp.sys_location = snmp_raw.get('sys_location')
                    snmp.sys_contact = snmp_raw.get('sys_contact')
                    trap_ips = snmp_raw.get('trap_ips')
                    if isinstance(trap_ips, list):
                        snmp.trap_ips = trap_ips
                    device.snmp = snmp

                cifs_raw = settings.get('cifs')
                if isinstance(cifs_raw, dict):
                    cifs = CIFS()
                    cifs.aio_support = parse_bool_from_raw(cifs_raw.get('aio_support'))
                    cifs.deny_access = parse_bool_from_raw(cifs_raw.get('deny_access'))
                    cifs.fruit_support = parse_bool_from_raw(cifs_raw.get('fruit_support'))
                    cifs.proto_level = cifs_raw.get('proto_level')
                    cifs.restrict_anonymous = parse_bool_from_raw(cifs_raw.get('restrict_anonymous'))
                    cifs.roundup_size = cifs_raw.get('roundup_size')
                    cifs.smb3 = parse_bool_from_raw(cifs_raw.get('smb3'))
                    cifs.smb3_encrypt = parse_bool_from_raw(cifs_raw.get('smb3_encrypt'))
                    device.cifs = cifs

        except Exception:
            logger.exception(f'Failed creating instance for filer {device_raw}')

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('guid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('serial_number') or '')

            device.uuid = device_raw.get('guid')
            device.description = device_raw.get('description')
            device.device_serial = device_raw.get('serial_number')

            settings = device_raw.get('settings')
            if isinstance(settings, dict):
                nasuni_time = settings.get('time')
                if isinstance(nasuni_time, dict):
                    device.last_seen = parse_date(nasuni_time.get('current_time_utc'))

            status = device_raw.get('status')
            if isinstance(status, dict):
                os_string = status.get('osversion')
                device.figure_os(os_string=os_string)

                uptime_in_sec = int_or_none(status.get('uptime'))
                if isinstance(uptime_in_sec, int) and uptime_in_sec:
                    uptime_in_days = int(uptime_in_sec / SECONDS_TO_DAY)
                    device.uptime = uptime_in_days

                platform = status.get('platform')
                if isinstance(platform, dict):
                    memory_mb = float_or_none(platform.get('memory'))
                    memory_gb = None
                    if isinstance(memory_mb, float):
                        memory_gb = float(memory_mb / 1000)  # From mb to gb
                    device.total_physical_memory = memory_gb

                    try:
                        cpu = platform.get('cpu')
                        if isinstance(cpu, dict):
                            mhz = float_or_none(cpu.get('frequency'))
                            if isinstance(mhz, float):
                                ghz = float(mhz / 1000)  # From mhz to ghz
                            else:
                                ghz = None
                            device.add_cpu(name=cpu.get('model'),
                                           cores=int_or_none(cpu.get('cores')),
                                           ghz=ghz)
                    except Exception:
                        logger.warning(f'Failed adding cpu of {cpu}')

            version = device_raw.get('build')
            if version:
                device.add_agent_version(agent=AGENT_NAMES.nasuni,
                                         version=version)

            self._fill_nasuni_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Nasuni Filer for {device_raw}')
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
                logger.exception(f'Problem with fetching Nasuni Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
