import logging

from axonius.adapter_base import AdapterProperty
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.splunk.connection import SplunkConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.clients.rest.connection import RESTConnection
from axonius.smart_json_class import SmartJsonClass
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file


logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-instance-attributes
class NetscalerData(SmartJsonClass):
    dst = Field(str, 'Destination')
    dst_port = Field(str, 'Destination Port')
    source = Field(str, 'Source')
    source_port = Field(str, 'Source Port')
    vserver = Field(str, 'VServer')
    vserver_port = Field(str, 'VServer Port')
    nat = Field(str, 'NAT')
    nat_port = Field(str, 'NAT Port')
    send = Field(int, 'Send Bytes')
    recv = Field(int, 'Recbv Bytes')
    raw_splunk_insertion_time = Field(str, 'Splunk insertion time')


class NetscalerSplunkAdapter(ScannerAdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        netscaler_data = ListField(NetscalerData, 'Netscaler')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return '{}:{}'.format(client_config['host'], client_config['port'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('host'), client_config.get('port'))

    def _connect_client(self, client_config):
        has_token = bool(client_config.get('token'))
        maybe_has_user = bool(client_config.get('username')) or bool(client_config.get('password'))
        has_user = bool(client_config.get('username')) and bool(client_config.get('password'))
        if has_token and maybe_has_user:
            msg = f'Different logins for Splunk domain ' \
                  f'{client_config.get("host")}, user: {client_config.get("username", "")}'
            logger.error(msg)
            raise ClientConnectionException(msg)
        if maybe_has_user and not has_user:
            msg = f'Missing credentials for Splunk [] domain ' \
                  f'{client_config.get("host")}, user: {client_config.get("username", "")}'
            logger.error(msg)
            raise ClientConnectionException(msg)
        try:
            connection = SplunkConnection(**client_config)
            with connection:
                pass
            return connection
        except Exception as e:
            message = 'Error connecting to client {0}, reason: {1}'.format(self._get_client_id(client_config), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific Splunk domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a Splunk connection

        :return: A json with all the attributes returned from the Splunk Server
        """
        with client_data:
            yield from client_data.get_devices(f'-{self.__max_log_history}d',
                                               self.__maximum_records,
                                               self.__fetch_plugins,
                                               splunk_macros_list=None,
                                               splunk_sw_macros_list=None)

    def _clients_schema(self):
        """
        The schema SplunkAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'host',
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'format': 'port'
                },
                {
                    'name': 'scheme',
                    'title': 'Protocol',
                    'type': 'string',
                    'enum': ['http', 'https'],
                    'default': 'https'
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
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string'
                }
            ],
            'required': [
                'host',
                'port',
                'scheme'
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        dst_dict = dict()
        for device_raw, device_type in devices_raw_data:
            try:
                netscaler_data = NetscalerData()
                netscaler_data.raw_splunk_insertion_time = parse_date(device_raw.get('raw_splunk_insertion_time'))
                if 'Netscaler' in device_type:
                    dst = device_raw.get('dst')
                    dst_port = None
                    if ':' in dst:
                        dst, dst_port = dst.split(':')[0], dst.split(':')[1]
                    netscaler_data.dst = dst
                    netscaler_data.dst_port = dst_port
                    source = device_raw.get('source')
                    source_port = None
                    if ':' in source:
                        source, source_port = source.split(':')[0], source.split(':')[1]
                    netscaler_data.source = source
                    netscaler_data.source_port = source_port
                    vserver = device_raw.get('vserver')
                    vserver_port = None
                    if ':' in source:
                        vserver, vserver_port = vserver.split(':')[0], vserver.split(':')[1]
                    netscaler_data.vserver = vserver
                    netscaler_data.vserver_port = vserver_port
                    nat = device_raw.get('nat')
                    nat_port = None
                    if ':' in source:
                        nat, nat_port = nat.split(':')[0], nat.split(':')[1]
                    netscaler_data.nat = nat
                    netscaler_data.nat_port = nat_port
                    try:
                        netscaler_data.recv = int(device_raw.get('recv'))
                    except Exception:
                        pass
                    try:
                        netscaler_data.send = int(device_raw.get('send'))
                    except Exception:
                        pass
                    if dst not in dst_dict:
                        dst_dict[dst] = []
                    dst_dict[dst].append(netscaler_data)
            except Exception:
                logger.exception(f'Problem getting device {device_raw}')
        for dst, netscaler_data in dst_dict.items():
            try:
                device = self._new_device_adapter()
                device.add_nic(ips=[dst])
                device.netscaler_data = netscaler_data
                yield device
            except Exception:
                logger.exception(f'Problem with dst {dst}')

    def _on_config_update(self, config):
        logger.info(f'Loading Splunk config: {config}')
        self.__max_log_history = int(config['max_log_history'])
        self.__maximum_records = int(config['maximum_records'])
        self.__fetch_plugins = {'fetch_netscaler_only': True
                                }

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'max_log_history',
                    'title': 'Number of days to fetch',
                    'type': 'number'
                },
                {
                    'name': 'maximum_records',
                    'title': 'Maximum amount of records per search',
                    'type': 'number'
                }
            ],
            'required': [
                'max_log_history',
                'maximum_records'
            ],
            'pretty_name': 'Netscaler Splunk Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'max_log_history': 30,
            'maximum_records': 100000,
        }

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
