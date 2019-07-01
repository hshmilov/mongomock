import logging
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from mobileiron_adapter.consts import DEVICE_PER_PAGE, MAX_DEVICES_COUNT


class MobileironConnection(RESTConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, headers={'Content-Type': 'application/json',
                                         'Accept': 'application/json'},
                         **kwargs)
        self.__fetch_apps = False
        self._users_dict = {}

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('No user name or password')
        self._get('ping', do_basic_auth=True)

    def _update_users_dict(self):
        try:
            total_count = DEVICE_PER_PAGE
            offset = 0
            while offset < min(total_count, MAX_DEVICES_COUNT):
                response = self._get('authorized/users', url_params={'adminDeviceSpaceId': self._device_space_id,
                                                                     'limit': DEVICE_PER_PAGE,
                                                                     'offset': offset, 'query': ''})
                for user_raw in response['results']:
                    if user_raw.get('principal'):
                        self._users_dict[user_raw.get('principal')] = user_raw
                total_count = response.get('totalCount')
                offset += DEVICE_PER_PAGE
        except Exception:
            logger.exception(f'Bad users response')

    def get_device_list(self, fetch_apps: bool = True):
        self.__fetch_apps = fetch_apps
        self._device_space_id = self._get('device_spaces/mine')['results'][0]['id']
        self._update_users_dict()
        count = self._get(
            'devices/count', url_params={'adminDeviceSpaceId': self._device_space_id, 'query': ''})['totalCount']
        # We use only these fields, and when I tried to fetch all the fields the query gave me HTTP 400
        fields = 'common.id,common.uuid,ios.DeviceNamem,common.platform,common.ip_address,' \
                 'common.wifi_mac_address,common.client_version,common.model,android.security_patch,' \
                 'user.user_id,common.miclient_last_connected_at,common.imei,common.storage_capacity,' \
                 'user.email_address,common.current_phone_number,common.last_connected_at,' \
                 'common.imsi,common.device_encrypted,common.device_is_compromised,common.device_admin_enabled' \
                 'windows_phone.win10_antivirus_status,windows_phone.health_data_bit_locker_status'
        offset = 0
        while offset < min(count, MAX_DEVICES_COUNT):
            try:
                logger.debug(f'Fetching devices {offset} to {offset+DEVICE_PER_PAGE}')
                paged_devices_list = self._get('devices', url_params={'adminDeviceSpaceId': self._device_space_id,
                                                                      'limit': DEVICE_PER_PAGE,
                                                                      'offset': offset, 'query': '',
                                                                      'fields': fields,
                                                                      'sortOrder': 'ASC',
                                                                      'sortField': 'user.display_name'})['results']
                if self.__fetch_apps:
                    device_apps_requests_async = []
                    device_apps_requests_devices_raw = []
                    for device_raw in paged_devices_list:
                        device_uuid = device_raw.get('common.uuid')
                        if device_uuid:
                            device_apps_requests_async.append(
                                {
                                    'name': 'devices/appinventory',
                                    'url_params':
                                        {'deviceUuids': str(device_uuid), 'adminDeviceSpaceId': self._device_space_id},
                                    'do_basic_auth': True
                                }
                            )
                            device_apps_requests_devices_raw.append(device_raw)
                    for device_raw_async, device_apps_response in zip(device_apps_requests_devices_raw,
                                                                      self._async_get(device_apps_requests_async)):
                        if self._is_async_response_good(device_apps_response):
                            try:
                                if isinstance(device_apps_response['results'], list) \
                                        and len(device_apps_response['results']) > 0:
                                    device_raw_async['appInventory'] = \
                                        device_apps_response['results'][0]['appInventory']
                                else:
                                    device_raw_async['appInventory'] = []
                            except Exception:
                                logger.exception(
                                    f'Exceptionw while parsing device apps from response {device_apps_response}, '
                                    f'device_raw is {device_raw_async}, yielding without apps')
                        else:
                            logger.error(f'Error getting apps for device')
                for device_raw in paged_devices_list:
                    yield device_raw, self._users_dict
            except Exception:
                logger.exception(f'Problem fetching devices at offset {offset}')
                break
            offset += DEVICE_PER_PAGE
