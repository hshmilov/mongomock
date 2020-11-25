import logging

from typing import Optional

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.json import from_json
from airwatch_adapter.consts import ENROLLED_DEVICE, NOT_ENROLLED_DEVICE, PAGE_SIZE, MAX_APPS_NUMBER, \
    MAX_DEVICES_NUMBER, ERROR_MUTED_SUBENDPOINTS, DEVICE_EXTENDED_INFO_KEY, DEVICES_ENDPOINT, APPS_SUBENDPOINT, \
    NETWORK_SUBENDPOINT, NOTES_SUBENDPOINT, TAGS_SUBENDPOINT, PROFILES_SUBENDPOINT

logger = logging.getLogger(f'axonius.{__name__}')


class AirwatchConnection(RESTConnection):

    def _connect(self):
        if self._username is None or self._password is None:
            raise RESTException('No user name or password or API key')

        # Note that the following self._get will have the application/xml Accept type,
        # but only afterwards we will update session headers to application/json.
        # when having both 'Accept' in permanent and session headers, session wins.

        try:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 0}, do_basic_auth=True)
        except Exception:
            self._get('mdm/devices/search', url_params={'pagesize': 1, 'page': 1}, do_basic_auth=True)

    @staticmethod
    def _prepare_async_dict(request_dict):
        return {'do_basic_auth': True,
                # Ask to return raw text so we will perform the from_json to mute exception logs
                'return_response_raw': False, 'use_json_in_response': False,
                **request_dict}

    def _parse_subendpoint_async_response(self, response, subendpoint, request_dict) -> Optional[dict]:

        if not self._is_async_response_good(response):
            logger.warning(f'Async response returned bad for request {request_dict}, got: {response}')
            return None

        # Note: We parse json here so we can suppress error logging for optional sub-endpoints
        try:
            response = from_json(response)
        except Exception:
            # optional subendpoints are not reported on failure
            if subendpoint in ERROR_MUTED_SUBENDPOINTS:
                return None
            logger.exception(f'Invalid response retrieved for request {request_dict}')
            return None

        return response

    def _paginated_async_get_devices(self, endpoint: str, page_size: int, async_chunks: int):

        # get first page of raw devices
        try:
            devices_search_raw = self._get(
                endpoint, url_params={'pagesize': page_size, 'page': 0}, do_basic_auth=True)
            pages_count = 1
        except Exception:
            devices_search_raw = self._get(
                endpoint, url_params={'pagesize': page_size, 'page': 1}, do_basic_auth=True)
            pages_count = 2
        yield from (devices_search_raw.get('Devices') or [])

        # retrieve the rest of the raw devices using async requests
        device_raw_requests = []
        total_count = min(devices_search_raw.get('Total', 1), MAX_DEVICES_NUMBER)
        while total_count > pages_count * page_size:
            try:
                device_raw_requests.append({
                    'name': endpoint,
                    'url_params': {'pagesize': page_size,
                                   'page': pages_count},
                    'do_basic_auth': True,
                })
            except Exception:
                logger.exception(f'Got problem fetching page {pages_count}')
            pages_count += 1

        # fill up device_raw_list
        for response in self._async_get(device_raw_requests, retry_on_error=True, chunks=async_chunks):
            if not self._is_async_response_good(response):
                logger.error(f'Async response returned bad, its {response}')
                continue

            if not isinstance(response, dict):
                logger.warning(f'Invalid response returned: {response}')
                continue

            yield from (response.get('Devices') or [])

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, arguments-differ, too-many-arguments
    def get_device_list(
            self,
            async_chunks: Optional[int] = None,
            page_size: Optional[int] = None,
            socket_recv_session_timeout: Optional[int] = None,
            fetch_not_enrolled_devices: bool=True,
            fetch_extended_details: bool=True,
            fetch_device_apps: bool=True,
            fetch_device_networks: bool=True,
            fetch_device_notes: bool=True,
            fetch_device_tags: bool=True,
            fetch_device_profiles: bool=True,
    ):
        serials_imei_set = set()

        page_size = page_size if page_size else PAGE_SIZE

        # prepare async requests for device info
        device_raw_by_device_id = {}
        async_requests = []

        # For the initial pagination the session timeout should be big
        self._requested_session_timeout = (10, 300)
        self.revalidate_session_timeout()
        # Notice that the page size here stays the default and not what the user configured.
        # We do this to get better results in particular in this request which could be slower.
        for device_raw in self._paginated_async_get_devices('mdm/devices/search', PAGE_SIZE, async_chunks):
            try:
                device_id = (device_raw.get('Id') or {}).get('Value') or 0
                if device_id == 0:
                    logger.exception(f'No id for device {device_raw}')
                    continue
            except Exception:
                logger.exception(f'Problem getting id for {device_raw}')
                continue
            device_raw_by_device_id.setdefault(str(device_id), device_raw)

            curr_device_requests = []
            # request extended device information
            if fetch_extended_details:
                curr_device_requests.append({
                    'name': f'{DEVICES_ENDPOINT}/{str(device_id)}'
                })

            if fetch_device_apps:
                curr_device_requests.append({
                    'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{APPS_SUBENDPOINT}',
                    # Retrieve apps initial page. if needed, additional pages would be requested later
                    'url_params': {'pagesize': page_size, 'page': 0}})

            if fetch_device_networks:
                curr_device_requests.append({'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{NETWORK_SUBENDPOINT}'})

            if fetch_device_notes:
                curr_device_requests.append({'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{NOTES_SUBENDPOINT}'})

            if fetch_device_tags:
                curr_device_requests.append({'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{TAGS_SUBENDPOINT}'})

            if fetch_device_profiles:
                curr_device_requests.append({'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{PROFILES_SUBENDPOINT}'})

            async_requests.extend(self._prepare_async_dict(request_dict)
                                  for request_dict in curr_device_requests)

            if device_raw.get('SerialNumber'):
                serials_imei_set.add(device_raw.get('SerialNumber'))
            if device_raw.get('Imei'):
                serials_imei_set.add(device_raw.get('Imei'))

        # now each response should be smaller and so the recv timeout can be smaller as well.
        if socket_recv_session_timeout:
            session_timeout = self._session_timeout
            if not session_timeout:
                session_timeout = (5, socket_recv_session_timeout)
            else:
                session_timeout = (session_timeout[0], socket_recv_session_timeout)

            self._requested_session_timeout = session_timeout
            self.revalidate_session_timeout()

        # run the async requests
        # prepare for additional requests, e.g. apps additional pages
        additional_async_requests = []

        # Note: we zip together responses with their originating request
        for request_dict, response in zip(async_requests, self._async_get(async_requests, retry_on_error=True,
                                                                          chunks=async_chunks)):
            try:
                # Note: if this line does not evaluate correctly - it is a serious bug that be caught at except below.
                # extract subendpoint part from url, e.g. mdm/devices/1/apps -> "1/apps"
                devices_subendpoint_part = request_dict.get('name').split('/', 2)[2]
                if '/' in devices_subendpoint_part:
                    device_id, response_subendpoint = devices_subendpoint_part.split('/', 2)[:2]
                else:
                    # Handle devices endpoint (mdm/devices/DEVICE_ID)
                    device_id, response_subendpoint = devices_subendpoint_part, DEVICE_EXTENDED_INFO_KEY

                device_raw = device_raw_by_device_id[device_id]
                # default subendpoint response to None to mark we got its response,
                #   it would be adjusted to the correct value later
                device_raw.setdefault(response_subendpoint, None)
            except Exception:
                logger.warning(f'failed to locate subendpoint for request {request_dict}, response: {response}')
                continue

            response = self._parse_subendpoint_async_response(response, response_subendpoint, request_dict)
            if not response:
                continue

            if not isinstance(response, (dict, list)):
                logger.warning(f'invalid {response_subendpoint} response returned: {response}')
                return

            if response_subendpoint == NETWORK_SUBENDPOINT:
                device_raw['Network'] = response
                continue

            # the rest of the endpoints require a dict
            if not isinstance(response, dict):
                logger.warning(f'invalid {response_subendpoint} response returned: {response}')
                return

            if response_subendpoint == APPS_SUBENDPOINT:
                device_raw.setdefault('DeviceApps', []).extend(response.get('DeviceApps') or [])

                # try to append additional pages for later handling
                # Note: if we got here, it means fetch_device_apps==True, no need for additional checks
                try:
                    total_count = min(response.get('Total', 1), MAX_APPS_NUMBER)
                    pages_count = 1
                    while total_count > pages_count * page_size:
                        try:
                            additional_async_requests.append(self._prepare_async_dict({
                                'name': f'{DEVICES_ENDPOINT}/{str(device_id)}/{APPS_SUBENDPOINT}',
                                'url_params': {'pagesize': page_size, 'page': pages_count}}))
                        except Exception:
                            logger.exception(f'Got problem fetching app for {device_raw} in page {pages_count}')
                        pages_count += 1

                except Exception:
                    logger.exception(f'Problem fetching apps for {device_raw}')

                continue

            elif response_subendpoint == NOTES_SUBENDPOINT:
                device_raw['DeviceNotes'] = response.get('DeviceNotes')
                continue

            elif response_subendpoint == TAGS_SUBENDPOINT:
                device_raw['DeviceTags'] = response.get('Tag')
                continue

            elif response_subendpoint == PROFILES_SUBENDPOINT:
                device_raw['profiles_raw'] = response.get('DeviceProfiles')
                continue

            elif response_subendpoint == DEVICE_EXTENDED_INFO_KEY:
                device_raw[DEVICE_EXTENDED_INFO_KEY] = response
                continue

            else:
                logger.error(f'Unknown subendpoint returned "{response_subendpoint}": {response}')
                continue

        # perform the additional apps pages requests
        for request_dict, response in zip(additional_async_requests,
                                          self._async_get(additional_async_requests, retry_on_error=True,
                                                          chunks=async_chunks)):
            try:
                # Note: if this line does not evaluate correctly - it is a serious bug that be caught at except below.
                device_id, response_subendpoint = request_dict.get('name').rstrip('/').rsplit('/', 2)[-2:]
                device_raw = device_raw_by_device_id[device_id]
            except Exception:
                logger.warning(f'failed to locate subendpoint for request {request_dict}, response: {response}')
                continue

            response = self._parse_subendpoint_async_response(response, response_subendpoint, request_dict)
            if not response:
                continue

            if response_subendpoint == APPS_SUBENDPOINT:
                device_raw.setdefault('DeviceApps', []).extend(response.get('DeviceApps') or [])

            else:
                logger.error(f'Unknown subendpoint returned "{response_subendpoint}": {response}')
                continue

        # yield enrolled devices
        for device_raw in device_raw_by_device_id.values():
            yield device_raw, ENROLLED_DEVICE

        if not fetch_not_enrolled_devices:
            return
        self._session_headers['Accept'] = 'application/json;version=2'
        uuid_list = []
        try:
            uuids_raw = self._get('system/groups/search', do_basic_auth=True)['OrganizationGroups']
            for uuid_raw in uuids_raw:
                if uuid_raw.get('Uuid'):
                    uuid_list.append(uuid_raw.get('Uuid'))
        except Exception:
            pass
        try:
            group_devices_requests = [self._prepare_async_dict({'name': f'mdm/dep/groups/{uuid_id}/devices'})
                                      for uuid_id in uuid_list]
            for request_dict, response in zip(group_devices_requests,
                                              self._async_get(group_devices_requests, retry_on_error=True,
                                                              chunks=async_chunks)):

                group_device_raw_list = self._parse_subendpoint_async_response(response, 'group devices', request_dict)
                if not isinstance(group_device_raw_list, list):
                    continue
                logger.info(f'Got {len(group_device_raw_list)} Group devices for request {request_dict}')

                for device_raw in group_device_raw_list:
                    if device_raw.get('deviceImei') and device_raw.get('deviceImei') in serials_imei_set:
                        continue
                    if device_raw.get('deviceSerialNumber')\
                            and device_raw.get('deviceSerialNumber') in serials_imei_set:
                        continue
                    yield device_raw, NOT_ENROLLED_DEVICE
        except Exception:
            logger.exception(f'Problem getting not enrolled devices')
