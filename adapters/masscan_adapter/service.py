import json
import logging

from axonius.adapter_base import AdapterProperty
from axonius.consts import remote_file_consts
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.remote_file_utils import (load_remote_data,
                                             test_file_reachability)

logger = logging.getLogger(f'axonius.{__name__}')


class MasscanAdapter(ScannerAdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        file_name = Field(str, 'Masscan File Name')
        banners = ListField(str, 'Banners')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return client_config['user_id']

    def _test_reachability(self, client_config):
        return test_file_reachability(client_config)

    def _connect_client(self, client_config):
        self.create_masscan_info_from_client_config(client_config)
        return client_config

    # pylint: disable=too-many-branches, too-many-statements
    @staticmethod
    def create_masscan_info_from_client_config(client_config):
        file_name, masscan_data = load_remote_data(client_config)
        masscan_json = json.loads(masscan_data)
        if not masscan_json or not isinstance(masscan_json, list) \
                or not isinstance(masscan_json[0], dict) or not masscan_json[0].get('ip'):
            raise Exception(f'Bad Masscan Json')
        return masscan_json, file_name

    def _query_devices_by_client(self, client_name, client_data):
        return self.create_masscan_info_from_client_config(client_data)

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks, arguments-differ
    def _parse_raw_data(self, devices_raw_data_full):
        devices_raw_data, file_name = devices_raw_data_full
        devices_raw_data_merge = dict()
        for data_raw in devices_raw_data:
            try:
                if not data_raw.get('ip'):
                    continue
                if data_raw.get('ip') not in devices_raw_data_merge:
                    devices_raw_data_merge[data_raw.get('ip')] = []
                devices_raw_data_merge[data_raw.get('ip')].append(data_raw)
            except Exception:
                logger.exception(f'Problem with data {data_raw}')
        for device_raw_list in devices_raw_data_merge.values():
            try:
                device = self._new_device_adapter()
                device.file_name = file_name
                device.id = device_raw_list[0].get('ip')
                device.add_nic(ips=[device_raw_list[0].get('ip')])
                last_seen = None
                try:
                    for device_raw in device_raw_list:
                        if device_raw.get('timestamp'):
                            last_seen_device = parse_date(int(device_raw.get('timestamp')))
                            if not last_seen or (last_seen_device and last_seen_device > last_seen):
                                last_seen = last_seen_device
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw_list}')
                device.last_seen = last_seen
                for device_raw in device_raw_list:
                    ports_raw = device_raw.get('ports')
                    if not isinstance(ports_raw, list):
                        ports_raw = []
                    for port_raw in ports_raw:
                        try:
                            device.add_open_port(protocol=port_raw.get('proto'),
                                                 port_id=port_raw.get('port'))
                            if port_raw.get('service') and port_raw.get('service').get('banner'):
                                device.banners.append(port_raw.get('service').get('banner'))
                        except Exception:
                            logger.exception(f'Problem with port raw {port_raw}')
                device.set_raw({'ips_list': device_raw_list})
                yield device
            except Exception:
                logger.exception(f'Problem adding device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
