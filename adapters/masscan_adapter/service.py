import logging
import urllib
import json
import requests
import chardet
# pylint: disable=import-error
from smb.SMBHandler import SMBHandler

from axonius.adapter_base import AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.scanner_adapter_base import ScannerAdapterBase
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.clients.rest.consts import get_default_timeout
from axonius.adapter_exceptions import ClientConnectionException
from axonius.utils.files import get_local_config_file


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
        raise NotImplementedError()

    def _connect_client(self, client_config):
        if not client_config.get('masscan_http') and 'masscan_file' not in client_config \
                and not client_config.get('masscan_share'):
            raise ClientConnectionException('Bad params. No File or URL or Share for masscan')
        self.create_masscan_info_from_client_config(client_config)
        return client_config

    def create_masscan_info_from_client_config(self, client_config):
        masscan_data_bytes = None
        if client_config.get('masscan_http'):
            try:
                masscan_data_bytes = requests.get(client_config.get('masscan_http'),
                                                  verify=False,
                                                  timeout=get_default_timeout()).content
            except Exception:
                logger.exception(f'Couldn\'t get masscan info from URL')
        elif client_config.get('masscan_share'):
            try:
                share_username = client_config.get('masscan_share_username')
                share_password = client_config.get('masscan_share_password')
                if not share_password or not share_username:
                    share_password = None
                    share_username = None
                share_path = client_config.get('masscan_share')
                if not share_path.startswith('\\\\'):
                    raise Exception('Bad Share Format')
                share_path = share_path[2:]
                share_path = share_path.replace('\\', '/')
                if share_username and share_password:
                    share_path = f'{urllib.parse.quote(share_username)}:' \
                                 f'{urllib.parse.quote(share_password)}@{share_path}'
                share_path = 'smb://' + share_path
                opener = urllib.request.build_opener(SMBHandler)
                with opener.open(share_path) as fh:
                    masscan_data_bytes = fh.read()
            except Exception:
                logger.exception(f'Couldn\'t get masscan info from share')
        elif 'masscan_file' in client_config:
            masscan_data_bytes = self._grab_file_contents(client_config['masscan_file'])
        if masscan_data_bytes is None:
            raise Exception('Bad masscan, could not parse the data')
        encoding = chardet.detect(masscan_data_bytes)['encoding']  # detect decoding automatically
        encoding = encoding or 'utf-8'
        masscan_data = masscan_data_bytes.decode(encoding)
        masscan_json = json.loads(masscan_data)
        if not masscan_json or not isinstance(masscan_json, list) \
                or not isinstance(masscan_json[0], dict) or not masscan_json[0].get('ip'):
            raise Exception(f'Bad Masscan Json')
        return masscan_json, client_config['user_id']

    def _query_devices_by_client(self, client_name, client_data):
        return self.create_masscan_info_from_client_config(client_data)

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'user_id',
                    'title': 'Masscan File Name',
                    'type': 'string'
                },
                {
                    'name': 'masscan_file',
                    'title': 'Masscan JSON File',
                    'description': 'The binary contents of the masscan XML File',
                    'type': 'file'
                },
                {
                    'name': 'masscan_http',
                    'title': 'Masscan JSON URL Path',
                    'type': 'string'
                },
                {
                    'name': 'masscan_share',
                    'title': 'Masscan JSON Share Path',
                    'type': 'string'
                },
                {
                    'name': 'masscan_share_username',
                    'title': 'Masscan Share User Name',
                    'type': 'string'
                },
                {
                    'name': 'masscan_share_password',
                    'title': 'Masscan Share Password',
                    'type': 'string',
                    'format': 'password'
                },
            ],
            'required': [
                'user_id',
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-nested-blocks, arguments-differ
    def _parse_raw_data(self, devices_raw_data_full):
        devices_raw_data, file_name = devices_raw_data_full
        for device_raw in devices_raw_data:
            try:
                device = self._new_device_adapter()
                device.file_name = file_name
                if not device_raw.get('ip'):
                    logger.warning(f'Bad device with no ip {device_raw}')
                    continue
                device.id = device_raw.get('ip')
                device.add_nic(ips=[device_raw.get('ip')])
                try:
                    device.last_seen = parse_date(int(device_raw.get('timestamp')))
                except Exception:
                    logger.exception(f'Problem getting last seen for {device_raw}')
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
                device.set_raw(device_raw)
                yield device
            except Exception:
                logger.exception(f'Problem adding device')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
