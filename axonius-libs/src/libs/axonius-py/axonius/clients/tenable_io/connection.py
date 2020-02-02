import logging
import time
# pylint: disable=import-error
from tenable.io import TenableIO

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import make_dict_from_csv
from axonius.clients.tenable_io.consts import AGENTS_PER_PAGE, DEVICES_PER_PAGE,\
    NUMBER_OF_SLEEPS, SECONDS_IN_DAY, TIME_TO_SLEEP,\
    DAYS_UNTIL_FETCH_AGAIN, DAYS_FOR_VULNS_IN_CSV, DAYS_VULNS_FETCH, MAX_AGENTS

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
        self._assets_list_dict = None
        self._vulns_list = None
        if self._username is not None and self._username != '' and self._password is not None and self._password != '':
            # We should use the user and password
            self._should_use_token = True
        elif self._access_key is not None and self._access_key != '' and \
                self._secret_key is not None and self._secret_key != '':
            # We should just use the given api keys
            self._should_use_token = False
            self._set_api_headers()
            self._tio = TenableIO(self._access_key, self._secret_key, proxies=self._proxies,
                                  vendor='Axonius', product='Axonius', build='1.0.0')
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
        self._patch(f'target-groups/{target_group_id}',
                    body_params={'members': ','.join(ips_raw),
                                 'type': 'user',
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

    def _connect(self):
        if self._should_use_token is True:
            response = self._post('session', body_params={'username': self._username, 'password': self._password})
            if 'token' not in response:
                error = response.get('errorCode', 'Unknown connection error')
                message = response.get('errorMessage', '')
                if message:
                    error = '{0}: {1}'.format(error, message)
                raise RESTException(error)
            self._set_token_headers(response['token'])
        else:
            self._get('scans')

    def _get_export_data(self, export_type, action=None, epoch=None):
        if epoch is None:
            epoch = self._epoch_last_run_time
        export_body_params = {'chunk_size': DEVICES_PER_PAGE[export_type]}
        if action is not None:
            export_body_params[action] = epoch
        export_uuid = self._post(f'{export_type}/export',
                                 body_params=export_body_params)['export_uuid']
        available_chunks = set()
        response = self._get(f'{export_type}/export/{export_uuid}/status')
        available_chunks.update(response.get('chunks_available', []))
        number_of_sleeps = 0
        while response.get('status') != 'FINISHED' and number_of_sleeps < NUMBER_OF_SLEEPS:
            try:
                response = self._get(f'{export_type}/export/{export_uuid}/status')
                available_chunks.update(response.get('chunks_available'))
            except Exception:
                logger.exception(f'Problem with getting chunks for {export_uuid}')
            time.sleep(TIME_TO_SLEEP)
            number_of_sleeps += 1
        for chunk_id in available_chunks:
            try:
                yield from self._get(f'{export_type}/export/{export_uuid}/chunks/{chunk_id}')
            except Exception:
                logger.exception(f'Problem in getting specific chunk {chunk_id} from {export_uuid} type {export_type}')

    def _get_assets(self, use_cache):
        if use_cache and \
                self._epoch_last_run_time + SECONDS_IN_DAY * DAYS_UNTIL_FETCH_AGAIN > int(time.time()):
            return
        if self._assets_list_dict is None:
            # new_assets = self._get_export_data('assets')
            new_assets = self._tio.exports.assets()
            updated_assets = []
            deleted_assets = []
            self._assets_list_dict = dict()
        else:
            new_assets = self._get_export_data('assets', action='created_at')
            updated_assets = self._get_export_data('assets', action='updated_at')
            deleted_assets = self._get_export_data('assets', action='deleted_at')

        # Creating dict out of assets_list
        for asset in new_assets:
            try:
                asset_id = asset.get('id', '')
                if asset_id is None or asset_id == '':
                    logger.warning(f'Got asset with no id. Asset raw data: {asset}')
                    continue
                self._assets_list_dict[asset_id] = asset
                self._assets_list_dict[asset_id]['vulns_info'] = []
            except Exception:
                logger.exception(f'Problem with asset {asset}')
        for deleted_asset in deleted_assets:
            try:
                del self._assets_list_dict[deleted_asset.get('id')]
            except Exception:
                logger.exception(f'Problem deleting asset: {deleted_asset}')
        for updated_asset in updated_assets:
            try:
                updated_id = updated_asset.get('id')
                if updated_id is not None and updated_id != '':
                    self._assets_list_dict[updated_id] = updated_asset
            except Exception:
                logger.exception(f'Problem updating asset {updated_asset}')

    def _get_vulns(self):
        yield from self._get_export_data('vulns', action='updated_at',
                                         epoch=int(time.time()) - (SECONDS_IN_DAY * DAYS_VULNS_FETCH))
        yield from self._get_export_data('vulns', action='created_at',
                                         epoch=int(time.time()) - (SECONDS_IN_DAY * DAYS_VULNS_FETCH))

    # pylint: disable=W0221
    def get_device_list(self, use_cache):
        try:
            self._get_assets(use_cache)
        except Exception:
            logger.exception('Couldnt get export trying to do benchmark')
            return self._get_device_list_csv(), 'csv'
        try:
            vulns_list = self._get_vulns()
        except Exception:
            vulns_list = []
            logger.exception('General error while getting vulnerabilities')
        try:
            for vuln_raw in vulns_list:
                try:
                    # Trying to find the correct asset for all vulnerability line in the array
                    asset_id_for_vuln = (vuln_raw.get('asset') or {}).get('uuid')
                    if not asset_id_for_vuln:
                        logger.warning(f'No id for vuln {vuln_raw}')
                        continue
                    self._assets_list_dict[asset_id_for_vuln]['vulns_info'].append(vuln_raw)
                except Exception:
                    logger.debug(f'Problem with vuln raw {vuln_raw}')
        except Exception:
            logger.exception('General error while getting vulnerabilities fetch')
        self._epoch_last_run_time = int(time.time())
        assets_list_dict = self._assets_list_dict
        if not use_cache:
            self._assets_list_dict = None
        return assets_list_dict.items(), 'export'

    def _get_device_list_csv(self):
        file_id = self._get('workbenches/export', url_params={'format': 'csv',
                                                              'report': 'vulnerabilities',
                                                              'chapter': 'vuln_by_asset',
                                                              'date_range': DAYS_FOR_VULNS_IN_CSV})['file']
        status = self._get(f'workbenches/export/{file_id}/status')['status']
        sleep_times = 0
        while status != 'ready' and sleep_times < NUMBER_OF_SLEEPS:
            time.sleep(TIME_TO_SLEEP)
            status = self._get(f'workbenches/export/{file_id}/status')['status']
            sleep_times += 1
        return make_dict_from_csv(self._get(f'workbenches/export/{file_id}/download',
                                            use_json_in_response=False).decode('utf-8'))

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
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
