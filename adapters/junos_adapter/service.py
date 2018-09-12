import logging

from ncclient.operations.rpc import RPCError
from jnpr.junos.exception import RpcError

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.files import get_local_config_file
from axonius.clients.juniper import rpc
from axonius.clients.juniper.device import create_device, JuniperDeviceAdapter
from axonius.adapter_exceptions import ClientConnectionException
from junos_adapter.client import JunOSClient
from junos_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class JunosAdapter(AdapterBase):
    MyDeviceAdapter = JuniperDeviceAdapter

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            with JunOSClient(**client_config) as client:
                return client
        except Exception as e:
            logger.error('Failed to connect to client %s',
                         self._get_client_id(client_config))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client):
        with client:
            for type_, func in [
                    ('ARP Device', client.query_arp_table),
                    ('FDB Device', client.query_fdb_table),
                    ('LLDP Device', client.query_lldp_neighbors),
                    ('Juniper Device', client.query_basic_info),
            ]:
                try:
                    if type_ == 'Juniper Device':
                        yield (type_, func())
                    else:
                        yield (type_, (client._host, func()))
                except (RPCError, RpcError) as e:
                    logger.error(f'Failed to execute RPC Command: {str(e)}')
                except Exception:
                    logger.exception('Failed to execute query')

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'host',
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string',
                    'description': 'Username for SSH'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password',
                    'description': 'Password for SSH'
                },
                {
                    'name': 'port',
                    'title': 'Protocol port',
                    'type': 'integer',
                    'description': 'SSH Port (Default: 22)'
                },
            ],
            'required': [
                'username',
                'password',
                'host',
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, raw_datas):
        for type_, raw_data in raw_datas:
            try:
                if type_ != 'Juniper Device':
                    raw_data = [raw_data]

                raw_data = rpc.parse_device(type_, raw_data)
                yield from create_device(self._new_device_adapter, type_, raw_data)
            except Exception:
                logger.exception(f'Error in handling {raw_data}')
                continue

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
