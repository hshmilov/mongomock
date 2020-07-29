import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.mixins.configurable import Configurable
from axonius.utils.parsing import is_domain_valid, parse_bool_from_raw, float_or_none, int_or_none
from axonius.utils.files import get_local_config_file
from remediant_secureone_adapter.connection import RemediantSecureoneConnection
from remediant_secureone_adapter.client_id import get_client_id
from remediant_secureone_adapter.structures import RemediantSecureoneDeviceInstance, ScanData, LocalAdminMap
from remediant_secureone_adapter.consts import DEFAULT_ASYNC_CHUNK_SIZE

logger = logging.getLogger(f'axonius.{__name__}')


class RemediantSecureoneAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(RemediantSecureoneDeviceInstance):
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
        connection = RemediantSecureoneConnection(domain=client_config['domain'],
                                                  verify_ssl=client_config['verify_ssl'],
                                                  https_proxy=client_config.get('https_proxy'),
                                                  proxy_username=client_config.get('proxy_username'),
                                                  proxy_password=client_config.get('proxy_password'),
                                                  username=client_config['username'],
                                                  apikey=client_config['apikey'])
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(chunk_size=self._chunk_size,
                                                   fetch_full_data=self._fetch_full_data)

    @staticmethod
    def _clients_schema():
        """
        The schema RemediantSecureoneAdapter expects from configs

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
                    'title': 'User ID',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Token',
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
                'apikey',
                'username',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_remediant_secureone_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.last_scanned = parse_date(device_raw.get('last_scanned'))
            device.last_seen = parse_date(device_raw.get('last_scanned'))
            scan_raw = device_raw.get('lastScan')
            if not isinstance(scan_raw, dict):
                scan_raw = {}
            device.last_scan_attempt = ScanData(msg=scan_raw.get('msg'),
                                                duration=float_or_none(scan_raw.get('duration')),
                                                success=parse_bool_from_raw(scan_raw.get('success')),
                                                scan_time=parse_date(scan_raw.get('scanTs')),
                                                error=scan_raw.get('error'))
            policy_raw = device_raw.get('policy')
            if not isinstance(policy_raw, dict):
                policy_raw = {}
            device.scan_policy = parse_bool_from_raw(policy_raw.get('scan'))
            device.secure_policy = parse_bool_from_raw(policy_raw.get('secure'))
            device.manage_local_sids_policy = parse_bool_from_raw(policy_raw.get('manage_local_sids'))
            device.strict_secure_policy = parse_bool_from_raw(policy_raw.get('strict_secure'))
            admins_raw = device_raw.get('admins')
            if not isinstance(admins_raw, dict):
                admins_raw = {}
            current_admins = admins_raw.get('current')
            if not isinstance(current_admins, list):
                current_admins = []
            for current_admin_raw in current_admins:
                try:
                    device.add_local_admin(admin_name=current_admin_raw.get('domainandname'))
                    admin_obj = LocalAdminMap(domain=current_admin_raw.get('domain'),
                                              domainandname=current_admin_raw.get('domainandname'),
                                              sidusage=int_or_none(current_admin_raw.get('sidusage')),
                                              sid=current_admin_raw.get('sid'),
                                              user=current_admin_raw.get('user'),
                                              svc_acct=parse_bool_from_raw(current_admin_raw.get('svc_acct')),
                                              on_host=parse_bool_from_raw(current_admin_raw.get('onHost')),
                                              inserted_ts=parse_date(current_admin_raw.get('inserted_ts')),
                                              user_id=current_admin_raw.get('userId'),
                                              expiring=current_admin_raw.get('expiring'),
                                              active=parse_bool_from_raw(current_admin_raw.get('active')),
                                              persistent=parse_bool_from_raw(current_admin_raw.get('persistent')))
                    device.local_admins_map.append(admin_obj)
                except Exception:
                    logger.exception(f'Problem with current admin {current_admin_raw}')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('distinguishedName')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('dNSHostName') or '')
            if device_raw.get('dNSHostName'):
                device.hostname = device_raw.get('dNSHostName')
            else:
                device.hostname = device_raw.get('cn')
            device.name = device_raw.get('cn')
            device.figure_os((device_raw.get('operatingSystem') or '') + ' ' +
                             (device_raw.get('operatingSystemVersion') or ''))
            domain = device_raw.get('domain_fqdn')
            if is_domain_valid(domain):
                device.domain = domain
            device.first_seen = parse_date(device_raw.get('inserted_ts'))
            if device_raw.get('last_ip'):
                device.add_nic(ips=[device_raw.get('last_ip')])
            self._fill_remediant_secureone_device_fields(device_raw, device)
            device.set_raw(device_raw)

            return device
        except Exception:
            logger.exception(f'Problem with fetching RemediantSecureone Device for {device_raw}')
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
                logger.exception(f'Problem with fetching RemediantSecureone Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Manager]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'chunk_size',
                    'type': 'integer',
                    'title': 'Number of requests to perform in parallel'
                },
                {
                    'name': 'fetch_full_data',
                    'type': 'bool',
                    'title': 'Fetch full devices data'
                }
            ],
            'required': [
                'chunk_size',
                'fetch_full_data'
            ],
            'pretty_name': 'Remediant Secureone Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'chunk_size': DEFAULT_ASYNC_CHUNK_SIZE,
            'fetch_full_data': False
        }

    def _on_config_update(self, config):
        # inject parallel_requests
        self._chunk_size = config.get('chunk_size') or DEFAULT_ASYNC_CHUNK_SIZE
        self._fetch_full_data = config.get('fetch_full_data') or False
