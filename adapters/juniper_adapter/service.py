import logging

from collections import defaultdict

from juniper_adapter import consts
from juniper_adapter.client import JuniperClient

from axonius.clients.juniper import rpc
from axonius.clients.juniper.device import create_device, JuniperDeviceAdapter, update_connected
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.mixins.configurable import Configurable
from axonius.adapter_exceptions import AdapterException, ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.utils.xml2json_parser import Xml2Json

logger = logging.getLogger(f'axonius.{__name__}')


class JuniperAdapter(AdapterBase, Configurable):
    """
    Connects axonius to Juniper devices
    """

    MyDeviceAdapter = JuniperDeviceAdapter

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': consts.JUNIPER_HOST,
                    'title': 'Host Name',
                    'type': 'string'
                },
                {
                    'name': consts.USER,  # The user needs System Configuration Read Privileges.
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
                consts.USER,
                consts.PASSWORD,
                consts.JUNIPER_HOST,
            ],
            'type': 'array'
        }

    def __parse_raw_data(self, devices_raw_data):
        others = defaultdict(list)
        for device_type, juno_device in devices_raw_data:
            if device_type == 'Juniper Space Device':
                try:
                    device = self._new_device_adapter()
                    device.device_type = device_type
                    device.name = juno_device.name
                    device.device_serial = str(juno_device.serialNumber)
                    device.id = device.device_serial
                    device.figure_os('junos')
                    device.device_model_family = str(juno_device.deviceFamily)
                    device.device_model = f'{str(juno_device.platform)} {str(juno_device.OSVersion)}'
                    ip_address = str(juno_device.ipAddr)
                    device.add_nic(None, [ip_address] if ip_address is not None else None)
                    device.connection_status = juno_device.connectionStatus
                    device.adapter_properties = [AdapterProperty.Network.name, AdapterProperty.Manager.name]
                    try:
                        json = Xml2Json(juno_device.xml_string())
                        device.set_raw(json.result)
                    except Exception:
                        logger.exception(f'Unable to set raw juniper space device')
                    yield device
                except Exception:
                    logger.exception(f'Got problems with {juno_device.name}')

            elif device_type == 'Juniper Device':
                raw_data = rpc.parse_device(device_type, juno_device)
                yield from create_device(self._new_device_adapter, device_type, raw_data)
            else:
                others[device_type].append(juno_device)

        # Now handle rpc
        for key, value in others.items():
            try:
                raw_data = rpc.parse_device(key, value)
                yield from create_device(self._new_device_adapter, key, raw_data)
            except Exception:
                logger.exception(f'Error in handling {value}')
                continue

    def _parse_raw_data(self, devices_raw_data):
        yield from update_connected(self.__parse_raw_data(devices_raw_data))

    def _query_devices_by_client(self, client_name, client_data):
        assert isinstance(client_data, JuniperClient)
        try:
            return client_data.get_all_devices(fetch_space_only=self.__fetch_space_only,
                                               do_async=self.__do_async)
        except Exception:
            logger.exception(f'Failed to get all the devices from the client: {client_data[consts.JUNIPER_HOST]}')
            raise AdapterException(f'Failed to get all the devices from the client: {client_data[consts.JUNIPER_HOST]}')

    def _get_client_id(self, client_config):
        return f'{client_config[consts.USER]}@{client_config[consts.JUNIPER_HOST]}'

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            return JuniperClient(url=f'https://{client_config[consts.JUNIPER_HOST]}',
                                 username=client_config[consts.USER],
                                 password=client_config[consts.PASSWORD])
        except Exception as e:
            logger.exception(
                f'Failed to connect to Juniper provider using this host {client_config[consts.JUNIPER_HOST]}')
            raise ClientConnectionException(
                f'Failed to connect to Juniper using this host {client_config[consts.JUNIPER_HOST]}: {e}'[:500])

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'do_async',
                    'title': 'Do Requests Async',
                    'type': 'bool'
                },
                {
                    'name': 'fetch_space_only',
                    'title': 'Fetch Junos Space Juniper Devices Only',
                    'type': 'bool'
                }
            ],
            'required': [
                'do_async',
                'fetch_space_only'
            ],
            'pretty_name': 'Junos Space Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'do_async': True,
            'fetch_space_only': False
        }

    def _on_config_update(self, config):
        self.__do_async = config['do_async']
        self.__fetch_space_only = config['fetch_space_only']
