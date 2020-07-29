import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, AGENT_NAMES
from axonius.fields import Field
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import GetDevicesError
from axonius.utils.parsing import make_dict_from_csv
from axonius.utils.remote_file_utils import load_remote_data, test_file_reachability
from axonius.consts import remote_file_consts

logger = logging.getLogger(f'axonius.{__name__}')


class ForcepointCsvAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        endpoint_server = Field(str, 'Endpoint Server')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    def _get_client_id(self, client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        return test_file_reachability(client_config)

    def _connect_client(self, client_config):
        if not self._test_reachability(client_config):
            raise ClientConnectionException('Configuration error.')
        return client_config

    # pylint:disable=arguments-differ
    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        file_name, csv_data = load_remote_data(client_data)
        return make_dict_from_csv(csv_data)

    def _clients_schema(self):
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    def _parse_raw_data(self, devices_raw_data):
        if 'Hostname' not in devices_raw_data.fieldnames:
            logger.error(f'Bad fields names{str(devices_raw_data.fieldnames)}')
            raise GetDevicesError(f'Bad fields names{str(devices_raw_data.fieldnames)}')
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                if not device_raw.get('Hostname'):
                    logger.warning(f'Bad device with no name {device_raw}')
                    continue
                device.hostname = device_raw.get('Hostname')
                device.id = device.hostname
                device.add_agent_version(agent=AGENT_NAMES.forcepoint_csv,
                                         version=device_raw.get('Client Installation Version'),
                                         status=device_raw.get('Client Status'))
                device.endpoint_server = device_raw.get('Endpoint Server')
                device.add_nic(None, device_raw.get('IP Address', '').split(','))
                device.last_used_users = device_raw.get('Logged-in Users', '').split(',')
                device.last_seen = parse_date(str(device_raw.get('Last Update', '')))
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device: {str(device_raw)}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
