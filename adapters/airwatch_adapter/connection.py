import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from airwatch_adapter.consts import ENROLLED_DEVICE, NOT_ENROLLED_DEVICE, PAGE_SIZE, MAX_APPS_NUMBER, MAX_DEVICES_NUMBER

logger = logging.getLogger(f'axonius.{__name__}')


class AirwatchConnection(RESTConnection):

    def _connect(self):
        if self._username is None or self._password is None:
            raise RESTException('No user name or password or API key')

        # Note that the following self._get will have the application/xml Accept type,
        # but only afterwards we will update session headers to application/json.
        # when having both 'Accept' in permanent and session headers, session wins.
        self._get('system/info', do_basic_auth=True, use_json_in_response=False)
        self._session_headers['Accept'] = 'application/json'

        try:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 0}, do_basic_auth=True)
        except Exception:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 1}, do_basic_auth=True)

    # pylint: disable=too-many-branches, too-many-statements
    def get_device_list(self):
        serials_imei_set = set()
        devices_raw_list = []
        try:
            devices_search_raw = self._get(
                'mdm/devices/search', url_params={'pagesize': PAGE_SIZE, 'page': 0}, do_basic_auth=True)
            pages_count = 1
        except Exception:
            devices_search_raw = self._get(
                'mdm/devices/search', url_params={'pagesize': PAGE_SIZE, 'page': 1}, do_basic_auth=True)
            pages_count = 2
        devices_raw_list += devices_search_raw.get('Devices', [])
        total_count = min(devices_search_raw.get('Total', 1), MAX_DEVICES_NUMBER)
        while total_count > pages_count * PAGE_SIZE:
            try:
                devices_search_raw = self._get(
                    'mdm/devices/search', url_params={'pagesize': PAGE_SIZE, 'page': pages_count},
                    do_basic_auth=True)
                devices_raw_list += devices_search_raw.get('Devices', [])
            except Exception:
                logger.exception(f'Got problem fetching page {pages_count}')
            pages_count += 1

        for device_raw in devices_raw_list:
            try:
                device_id = device_raw.get('Id', {}).get('Value', 0)
                if device_id == 0:
                    logger.exception(f'No id for device {device_raw}')
                    continue
            except Exception:
                logger.exception(f'Problem getting id for {device_raw}')
                continue
            try:
                device_raw['Network'] = self._get(f'mdm/devices/{str(device_id)}/network', do_basic_auth=True)
            except Exception:
                logger.exception(f'Problem fetching network for {device_raw}')
            try:
                device_apps_list = []
                apps_search_raw = self._get(
                    f'mdm/devices/{str(device_id)}/apps', url_params={'pagesize': PAGE_SIZE, 'page': 0},
                    do_basic_auth=True)
                device_apps_list += apps_search_raw.get('DeviceApps', [])
                total_count = min(apps_search_raw.get('Total', 1), MAX_APPS_NUMBER)
                pages_count = 1
                while total_count > pages_count * PAGE_SIZE:
                    try:
                        apps_search_raw = self._get(
                            f'mdm/devices/{str(device_id)}/apps', url_params={'pagesize': PAGE_SIZE,
                                                                              'page': pages_count}, do_basic_auth=True)
                        device_apps_list += apps_search_raw.get('DeviceApps', [])
                    except Exception:
                        logger.exception(f'Got problem fetching app for {device_raw} in page {pages_count}')
                    pages_count += 1
                device_raw['DeviceApps'] = device_apps_list
            except Exception:
                logger.exception(f'Problem fetching apps for {device_raw}')
            try:
                device_raw['DeviceNotes'] = self._get(f'mdm/devices/{str(device_id)}/notes',
                                                      do_basic_auth=True)['DeviceNotes']
            except Exception:
                pass
            try:
                device_raw['DeviceTags'] = self._get(f'mdm/devices/{str(device_id)}/tags',
                                                     do_basic_auth=True)['Tag']
            except Exception:
                pass
            if device_raw.get('SerialNumber'):
                serials_imei_set.add(device_raw.get('SerialNumber'))
            if device_raw.get('Imei'):
                serials_imei_set.add(device_raw.get('Imei'))
            yield device_raw, ENROLLED_DEVICE
        self._session_headers['Accept'] = 'application/json;version=2'
        uuid_list = []
        try:
            uuids_raw = self._get('system/groups/search', do_basic_auth=True)['OrganizationGroups']
            for uuid_raw in uuids_raw:
                if uuid_raw.get('Uuid'):
                    uuid_list.append(uuid_raw.get('Uuid'))
        except Exception:
            pass
        for uuid_id in uuid_list:
            try:
                for device_raw in self._get(f'mdm/dep/groups/{uuid_id}/devices', do_basic_auth=True):
                    if device_raw.get('deviceImei') and device_raw.get('deviceImei') in serials_imei_set:
                        continue
                    if device_raw.get('deviceSerialNumber')\
                            and device_raw.get('deviceSerialNumber') in serials_imei_set:
                        continue
                    yield device_raw, NOT_ENROLLED_DEVICE
            except Exception:
                logger.exception(f'Problem getting not enrolled devices')
