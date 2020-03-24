import logging
from collections import defaultdict

from axonius.fields import Field
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter
from axonius.clients.mysql.connection import MySQLConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import get_exception_string
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
from mysql_special_adapter.client_id import get_client_id
from mysql_special_adapter.structures import HostDevices, CrawlerDevices
from mysql_special_adapter.consts import DEFAULT_MYSQL_SPECIAL_PORT, HOST_TABLE, CRAWLER_TABLE, \
    MYSQL_SPECIAL_CRAWLER_QUERY, MYSQL_SPECIAL_HOST_QUERY, MYSQL_SPECIAL_VMHOST_QUERY, MYSQL_SPECIAL_WHERE_CLAUSE

logger = logging.getLogger(f'axonius.{__name__}')
DEFAULT_PAGINATION = 1000


# pylint: disable=too-many-instance-attributes, logging-format-interpolation


class MysqlSpecialAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        host_devices = Field(HostDevices, 'Host devices')
        crawler_devices = Field(CrawlerDevices, 'Crawler devices')

    def __init__(self, *args, **kwargs):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        if not client_config['username'] or not client_config['password']:
            raise ClientConnectionException('No username or password')

        return RESTConnection.test_reachability(client_config.get('domain'),
                                                port=client_config.get('port') or DEFAULT_MYSQL_SPECIAL_PORT)

    # pylint: disable=no-self-use
    def _connect_client(self, client_config):
        try:
            connection = MySQLConnection(
                client_config['domain'],
                int(client_config.get('port') or DEFAULT_MYSQL_SPECIAL_PORT),
                client_config['username'],
                client_config['password'],
                client_config.get('database'))
            with connection:
                pass  # check that the connection credentials are valid
            return connection, client_config
        except Exception:
            message = f'Error connecting to client host: {client_config["domain"]}  ' \
                      f'database: ' \
                      f'{client_config.get("database")}'
            logger.exception(message)
            raise ClientConnectionException(get_exception_string())

    @staticmethod
    def _clients_schema():
        """
        The schema MysqlSpecialAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'SQL Server Host',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'SQL Server Port',
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
                    'name': 'database',
                    'title': 'SQL Server Database Name',
                    'type': 'string'
                },
            ],
            'required': [
                'domain',
                'username',
                'password',
                'database'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches
    @staticmethod
    def _fill_host_fields(device_raw, host_vm_intersect):
        try:
            host_instance = HostDevices()
            host_instance.p_key = device_raw.get('pkey')
            host_instance.uuid = device_raw.get('UUID')
            host_instance.cpumhz = device_raw.get('cpumhz')
            host_instance.cpu_model = device_raw.get('cpumodel')
            host_instance.box_model = device_raw.get('boxmodel')
            host_instance.nic_count = device_raw.get('niCcount')
            host_instance.moref = device_raw.get('moref')
            host_instance.vcenter = device_raw.get('vcenter')
            host_instance.scrapedate = parse_date(device_raw.get('scrapredate'))
            host_instance.data_center = device_raw.get('datacenter')
            host_instance.esxi_version = device_raw.get('esxiVersion')
            host_instance.build = device_raw.get('build')
            host_instance.on_vsan = device_raw.get('onVSAN')
            host_instance.cluster = device_raw.get('cluster')

            if device_raw.get('UUID') is not None:
                if host_vm_intersect.get(device_raw.get('UUID')) is not None:
                    host_instance.vms.extend(host_vm_intersect.get(device_raw.get('UUID')))

            return host_instance
        except Exception:
            logger.exception(f'Failed to parse host instance info for device {device_raw}')
            return None

    # pylint: disable=too-many-branches
    @staticmethod
    def _fill_crawler_fields(device_raw, vm_host_intersect):
        try:
            crawler_instance = CrawlerDevices()
            crawler_instance.p_key = device_raw.get('p_key')
            crawler_instance.vcenter = device_raw.get('vcenter')
            crawler_instance.path = device_raw.get('path')
            crawler_instance.uuid = device_raw.get('uuid')
            crawler_instance.guest_id = device_raw.get('guestid')
            crawler_instance.guest_state = device_raw.get('gueststate')
            crawler_instance.tools_running_status = device_raw.get('toolsRunningStatus')
            crawler_instance.tools_version = device_raw.get('toolsVersion')
            crawler_instance.tools_version_status2 = device_raw.get('toolsVersionStatus2')
            crawler_instance.disk = device_raw.get('disk')
            crawler_instance.bu_build = device_raw.get('BU')
            crawler_instance.scrape_date = parse_date(device_raw.get('scrapedate'))
            crawler_instance.shasum = device_raw.get('shasum')
            crawler_instance.moref = device_raw.get('moref')
            crawler_instance.vmx_path = device_raw.get('vmxPath')
            crawler_instance.host_uuid = device_raw.get('hostuuid')
            crawler_instance.data_stores = device_raw.get('datastores')
            crawler_instance.v_san = device_raw.get('vSAN')

            if device_raw.get('uuid') is not None:
                crawler_instance.host_machine = vm_host_intersect.get(device_raw.get('uuid'))

            return crawler_instance
        except Exception:
            logger.exception(f'Failed to parse crawler instance info for device {device_raw}')
            return None

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        connection, client_config = client_data
        connection.set_devices_paging(self.__devices_fetched_at_a_time)
        mysql_special_days_ago_clause = MYSQL_SPECIAL_WHERE_CLAUSE.format(days_ago=self.__scrape_date_days_ago)
        with connection:
            vm_host_intersect = {}
            host_vm_intersect = defaultdict(list)
            for device_raw in connection.query(MYSQL_SPECIAL_VMHOST_QUERY + mysql_special_days_ago_clause):
                if device_raw.get('vmUUId') is not None and device_raw.get('hostUUID') is not None:
                    vm_host_intersect[device_raw.get('vmUUId')] = device_raw.get('hostUUID')
                    host_vm_intersect[device_raw.get('hostUUID')].append(device_raw.get('vmUUId'))

            for device_raw in connection.query(MYSQL_SPECIAL_HOST_QUERY + mysql_special_days_ago_clause):
                yield device_raw, HOST_TABLE, vm_host_intersect, host_vm_intersect

            for device_raw in connection.query(MYSQL_SPECIAL_CRAWLER_QUERY + mysql_special_days_ago_clause):
                yield device_raw, CRAWLER_TABLE, vm_host_intersect, host_vm_intersect

    # pylint: disable=C0103
    def _parse_raw_data(self, devices_raw_data):
        for device_raw, device_source, vm_host_intersect, host_vm_intersect in devices_raw_data:
            if not device_raw:
                continue
            try:
                device = self._new_device_adapter()
                if device_raw.get('name') != 'null':
                    device.name = device_raw.get('name')

                if device_source == HOST_TABLE:
                    device.id = device_raw.get('name') + '_' + device_raw.get('UUID')
                    device.hostname = device_raw.get('name')
                    device.total_physical_memory = device_raw.get('memory') / (1024 ** 3)
                    device.host_devices = self._fill_host_fields(device_raw, host_vm_intersect)

                elif device_source == CRAWLER_TABLE:
                    device.id = device_raw.get('name') + '_' + device_raw.get('uuid')
                    device.total_physical_memory = device_raw.get('memory') / 1024
                    device.hostname = device_raw.get('dnsName')
                    device.total_number_of_physical_processors = device_raw.get('cpus')

                    ip_addresses = device_raw.get('ipAddress')
                    if not ip_addresses or str(ip_addresses).lower() == 'null':
                        ip_addresses = []
                    if isinstance(ip_addresses, str):
                        ip_addresses = ip_addresses.split(',')
                    if ip_addresses:
                        device.add_nic(ips=ip_addresses)

                    device.crawler_devices = self._fill_crawler_fields(device_raw, vm_host_intersect)

                if device:
                    device.set_raw({key: str(val) for key, val in device_raw.items()})
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

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
                    'name': 'scrape_date_days_ago',
                    'type': 'integer',
                    'title': 'Scrape Date (days ago)'
                }
            ],
            'required': ['devices_fetched_at_a_time', 'scrape_date_days_ago'],
            'pretty_name': 'MySQL Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'devices_fetched_at_a_time': 1000,
            'scrape_date_days_ago': 14
        }

    def _on_config_update(self, config):
        self.__devices_fetched_at_a_time = config['devices_fetched_at_a_time']
        self.__scrape_date_days_ago = config['scrape_date_days_ago']
