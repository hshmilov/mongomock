import json
import datetime
import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException

logger = logging.getLogger(f'axonius.{__name__}')


class SymantecSepCloudConnection(RESTConnection):
    """ rest client for SymantecSepCloud adapter """

    def __init__(self, *args, client_id, client_secret, **kwargs):
        super().__init__(*args, url_base_prefix='/v1',
                         headers={'Accept': 'application/json',
                                  'Content-Type': 'application/json',
                                  'Host': 'api.sep.securitycloud.symantec.com'},
                         **kwargs)
        self._username = client_id
        self._password = client_secret
        self._last_refresh = None
        self._expires_in = None

    def _refresh_token(self):
        if self._last_refresh and self._expires_in \
                and self._last_refresh + datetime.timedelta(seconds=self._expires_in) > datetime.datetime.now():
            return
        response = self._post('oauth2/tokens',
                              extra_headers={'Content-Type': 'application/x-www-form-urlencoded'},
                              body_params='grant_type=client_credentials',
                              use_json_in_body=False,
                              do_basic_auth=True)
        if 'access_token' not in response:
            raise RESTException(f'Bad response: {response}')
        self._token = response['access_token']
        self._session_headers['Authorization'] = f'Bearer {self._token}'
        self._last_refresh = datetime.datetime.now()
        self._expires_in = int(response['expires_in'])

    def _connect(self):
        if not self._username or not self._password:
            raise RESTException('Missing Critical Parameter')
        self._last_refresh = None
        self._refresh_token()
        groups_raw = self._get('device-groups')
        if not isinstance(groups_raw, dict) or not groups_raw.get('device_groups')\
                or not isinstance(groups_raw['device_groups'], list):
            raise RESTException(f'Bad Response: {groups_raw}')

    # pylint: disable=too-many-nested-blocks, too-many-branches, too-many-statements
    def get_device_list(self):
        groups_raw = self._get('device-groups')
        if not isinstance(groups_raw, dict) or not groups_raw.get('device_groups')\
                or not isinstance(groups_raw['device_groups'], list):
            raise RESTException(f'Bad Response: {groups_raw}')
        groups_ids = []
        for group_raw in groups_raw['device_groups']:
            if isinstance(group_raw, dict) and group_raw.get('id'):
                groups_ids.append(group_raw.get('id'))
        device_ids = set()
        for group_id in groups_ids:
            try:
                device_ids_raw = self._get(f'device-groups/{group_id}/devices')
                if not isinstance(device_ids_raw, dict) or not isinstance(device_ids_raw['devices'], list):
                    raise RESTException(f'Bad Response: {device_ids_raw}')
                for device_id_raw in device_ids_raw['devices']:
                    if isinstance(device_id_raw, dict) and device_id_raw.get('id'):
                        device_id = device_id_raw.get('id')
                        device_ids.add(device_id)
            except Exception:
                logger.exception(f'Problem with group id {group_id}')
        device_ids_requests = []
        for device_id in device_ids:
            device_ids_requests.append({'name': f'devices/{device_id}', 'use_json_in_response': False})
        for device_raw in self._async_get_only_good_response(device_ids_requests):
            try:
                final_lines = []
                for line in device_raw.splitlines():
                    try:
                        if ':' not in line:
                            final_lines.append(line)
                        else:
                            left_over = line.split(':')[-1]
                            if left_over.strip() == ',':
                                continue
                            final_lines.append(line)
                    except Exception:
                        logger.exception(f'Problem with line')
                yield json.loads('\n'.join(final_lines))
            except Exception:
                logger.exception(f'Bad json {device_raw}')
