import logging
import time
# pylint: disable=import-error

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.tenable_io.consts import AGENTS_PER_PAGE, MAX_AGENTS
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.clients.tenable_io.parse import get_export_asset_plus_vulns

logger = logging.getLogger(f'axonius.{__name__}')


class TenableIoConnection(RESTConnection):

    def __init__(self, *args, access_key: str = '',  secret_key: str = '', **kwargs):
        super().__init__(*args,
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'},
                         **kwargs)
        self._access_key = access_key
        self.plugins_dict = dict()
        self._secret_key = secret_key
        self._epoch_last_run_time = 0
        self._vulns_list = None
        if self._username is not None and self._username != '' and self._password is not None and self._password != '':
            # We should use the user and password
            self._should_use_token = True
        elif self._access_key is not None and self._access_key != '' and \
                self._secret_key is not None and self._secret_key != '':
            # We should just use the given api keys
            self._should_use_token = False
            self._set_api_headers()
        else:
            raise RESTException('Missing user/password or api keys')

    # pylint: disable=arguments-differ
    def _do_request(self, *args, **kwargs):
        nkwargs = kwargs.copy()
        nkwargs.pop('raise_for_status', None)
        nkwargs.pop('return_response_raw', None)
        nkwargs.pop('use_json_in_response', None)
        for try_ in range(4):
            response = super()._do_request(
                *args,
                raise_for_status=False,
                return_response_raw=True,
                use_json_in_response=False,
                **nkwargs
            )
            if response.status_code == 429:
                retry_after = int(response.headers.get('retry-after') or 2)
                logger.info(f'429: Retry After {retry_after}')
                time.sleep(retry_after)
                continue
            break
        else:
            raise RESTException(f'Failed to fetch because rate limit')
        return self._handle_response(response)

    def create_asset(self, tenable_io_dict):
        self._post('import/assets',
                   body_params={'assets': [tenable_io_dict],
                                'source': 'Axonius'})
        return True

    def add_ips_to_scans(self, tenable_io_dict):
        scan_name = tenable_io_dict.get('scan_name')
        ips = tenable_io_dict.get('ips')
        if not ips or not scan_name:
            raise RESTException('Missing IPS or Scan Name')
        scans_list = self._get('scans').get('scans')
        if not scans_list or not isinstance(scans_list, list):
            raise RESTException('Bad list of scans')
        scan_id = None
        for scan_raw in scans_list:
            if scan_raw.get('name') == scan_name:
                scan_id = scan_raw.get('id')
                break
        if not scan_id:
            raise RESTException('Couldn\'n find scan name')
        scan_raw = self._get(f'scans/{scan_id}')
        if not scan_raw or not isinstance(scan_raw, dict) or not scan_raw.get('info'):
            raise RESTException('Couldn\'n get scan id info')
        ips_final = [ip.strip() for ip in ips if ip.strip()]
        ips_str = ','.join(ips_final)
        uuid = scan_raw['info'].get('uuid')
        body_params = {'uuid': uuid,
                       'settings': {'name': scan_name,
                                    'text_targets': ips_str}}
        self._put(f'scans/{scan_id}', body_params=body_params)
        return True

    def get_uuid_to_id_scans_dict(self):
        uuid_to_id_dict = dict()
        scans_list = self._get('scans').get('scans')
        if not scans_list or not isinstance(scans_list, list):
            raise RESTException('Bad list of scans')
        for scan_raw in scans_list:
            if not isinstance(scan_raw, dict) or not scan_raw.get('id') or not scan_raw.get('uuid'):
                continue
            uuid_to_id_dict[scan_raw['uuid']] = str(scan_raw['id'])
        return uuid_to_id_dict

    def add_ips_to_target_group(self, tenable_io_dict):
        target_group_name = tenable_io_dict.get('target_group_name')
        ips = tenable_io_dict.get('ips')
        override = tenable_io_dict.get('override')
        if not ips or not target_group_name:
            raise RESTException('Missing IPS or Target Group ID')
        target_group_list = self._get('target-groups').get('target_groups')
        if not target_group_list or not isinstance(target_group_list, list):
            raise RESTException('Bad list of taget groups')
        target_group_id = None
        for target_group_raw in target_group_list:
            if target_group_raw.get('name') == target_group_name:
                target_group_id = target_group_raw.get('id')
                break
        if not target_group_id:
            raise RESTException('Couldn\'n find target group name')
        target_group_id_raw = self._get(f'target-groups/{target_group_id}')
        if not target_group_id_raw or not isinstance(target_group_id_raw, dict):
            raise RESTException('Couldn\'n get asset id info')
        if not target_group_id_raw.get('members'):
            raise RESTException('Device with no IPs')
        ips_raw = target_group_id_raw.get('members').split(',')
        if override:
            ips_raw = []
        for ip in ips:
            if ip not in ips_raw:
                ips_raw.append(ip)
        self._put(f'target-groups/{target_group_id}',
                  body_params={'members': ','.join(ips_raw),
                               'type': 'system',
                               'name': target_group_name})
        return True

    def create_target_group_with_ips(self, tenable_io_dict):
        target_group_name = tenable_io_dict.get('target_group_name')
        ips = tenable_io_dict.get('ips')
        if not ips or not target_group_name:
            raise RESTException('Missing IPS or Tagret Group ID')
        self._post(f'target-groups',
                   body_params={'members': ','.join(ips),
                                'type': 'system',
                                'name': target_group_name})
        return True

    def _set_token_headers(self, token):
        """ Sets the API token, in the appropriate header, for valid requests

        :param str token: API Token
        """
        self._token = token
        self._session_headers['X-Cookie'] = 'token={0}'.format(token)

    def _set_api_headers(self):
        self._permanent_headers['X-ApiKeys'] = f'accessKey={self._access_key}; secretKey={self._secret_key}'

    @staticmethod
    def _handle_tenable_io_response(response, just_raise_error=False):
        if just_raise_error or response.get('errorCode') or response.get('errorMessage'):
            error = response.get('errorCode', 'Unknown connection error')
            message = response.get('errorMessage', '')
            if message:
                error = '{0}: {1}'.format(error, message)
            raise RESTException(error)

    def _connect(self):
        if self._should_use_token is True:
            response = self._post('session', body_params={'username': self._username, 'password': self._password})
            if 'token' not in response:
                self._handle_tenable_io_response(response, just_raise_error=True)
            self._set_token_headers(response['token'])

        # Make sure there are sufficient permissions (Administrator Role)
        session = self._get('session')
        self._handle_tenable_io_response(session)

        if not session.get('permissions'):
            raise RESTException(f'Unable to retrieve permissions.'
                                f' make sure user was granted Administrator role')

        try:
            permissions = int(session['permissions'])
        except Exception:
            message = f'Invalid permissions found: {session["permissions"]}'
            logger.exception(message)
            raise RESTException(message)

        # see: https://developer.tenable.com/docs/permissions
        if permissions < 64:  # Administrator
            raise RESTException(f'Insufficient permissions found.'
                                f' Did you grant the user an Administrator Role?')

    # pylint: disable=W0221, too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def get_device_list(self, should_cancel_old_exports_jobs=False):
        if should_cancel_old_exports_jobs:
            for export_type in ['assets', 'vulns']:
                try:
                    assets_exports = self._get(f'{export_type}/export/status').get('exports') or []
                    for asset_export in assets_exports:
                        if asset_export.get('uuid'):
                            export_uuid = asset_export['uuid']
                            export_status = asset_export.get('status') or ''
                            if export_status.upper() in ['QUEUED', 'PROCESSING']:
                                try:
                                    self._post(f'{export_type}/export/{export_uuid}/cancel')
                                except Exception as e:
                                    logger.warning(f'Failed canceling export type {export_type} - '
                                                   f'{export_uuid}: {str(e)}')
                except Exception:
                    logger.exception(f'Problem with cancelling export type: {export_type}')

        result = (yield from concurrent_multiprocess_yield(
            [
                (
                    get_export_asset_plus_vulns,
                    (
                        self._access_key,
                        self._secret_key,
                        self._proxies
                    ),
                    {}
                )
            ],
            1
        ))
        return result

    def get_plugin_info(self, plugin_id):
        try:
            if self.plugins_dict.get(plugin_id):
                return self.plugins_dict[plugin_id]
            plugin_raw_data = self._get(f'plugins/plugin/{plugin_id}')
            if isinstance(plugin_raw_data.get('attributes'), list):
                self.plugins_dict[plugin_id] = plugin_raw_data.get('attributes')
                return self.plugins_dict[plugin_id]
        except Exception:
            logger.exception(f'Problem getting plugin data for {plugin_id}')
        return None

    def get_agents(self):
        try:
            scanners = self._get('scanners')['scanners']
            logger.info(f'Got {len(scanners)} scanners')
            scanners_ids = [scanner.get('id') for scanner in scanners if scanner.get('id')]
            for scanner_id in scanners_ids:
                try:
                    response = self._get(f'scanners/{scanner_id}/agents', url_params={'offset': 0,
                                                                                      'limit': AGENTS_PER_PAGE})
                    total = response['pagination']['total']
                    logger.info(f'Got {total} number of agents in {scanner_id}')
                    yield from response['agents']
                    offset = AGENTS_PER_PAGE
                    while offset < min(total, MAX_AGENTS):
                        try:
                            yield from self._get(f'scanners/{scanner_id}/agents',
                                                 url_params={'offset': offset,
                                                             'limit': AGENTS_PER_PAGE})['agents']
                        except Exception:
                            logger.exception(f'Problem with offset {offset}')
                        offset += AGENTS_PER_PAGE
                except Exception:
                    logger.exception(f'Problem getting agents from scanner id {scanner_id}')
        except Exception:
            logger.exception(f'Problem getting agents return none')
