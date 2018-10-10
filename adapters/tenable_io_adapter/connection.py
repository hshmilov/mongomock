import logging
import time

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.utils.parsing import make_dict_from_csv
from tenable_io_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class TenableIoConnection(RESTConnection):

    def __init__(self, *args, access_key: str = '',  secret_key: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._access_key = access_key
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
        else:
            raise RESTException('Missing user/password or api keys')

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
        export_body_params = {'chunk_size': consts.DEVICES_PER_PAGE[export_type]}
        if action is not None:
            export_body_params[action] = epoch
        export_uuid = self._post(f'{export_type}/export',
                                 body_params=export_body_params)['export_uuid']
        available_chunks = set()
        response = self._get(f'{export_type}/export/{export_uuid}/status')
        available_chunks.update(response.get('chunks_available', []))
        number_of_sleeps = 0
        while response.get('status') != 'FINISHED' and number_of_sleeps < consts.NUMBER_OF_SLEEPS:
            try:
                response = self._get(f'{export_type}/export/{export_uuid}/status')
                available_chunks.update(response.get('chunks_available'))
            except Exception:
                logger.exception(f'Problem with getting chunks for {export_uuid}')
            time.sleep(consts.TIME_TO_SLEEP)
            number_of_sleeps += 1
        export_list = []
        for chunk_id in available_chunks:
            try:
                export_list.extend(self._get(f'{export_type}/export/{export_uuid}/chunks/{chunk_id}'))
            except Exception:
                logger.exception(f'Problem in getting specific chunk {chunk_id} from {export_uuid} type {export_type}')
        return export_list

    def _get_assets(self):
        if self._epoch_last_run_time + consts.SECONDS_IN_DAY * consts.DAYS_UNTIL_FETCH_AGAIN > int(time.time()):
            return
        if self._assets_list_dict is None:
            new_assets = self._get_export_data('assets')
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
        vulns_list = self._get_export_data('vulns', action='updated_at',
                                           epoch=int(time.time()) - (consts.SECONDS_IN_DAY * consts.DAYS_VULNS_FETCH))
        vulns_list += self._get_export_data('vulns', action='created_at',
                                            epoch=int(time.time()) - (consts.SECONDS_IN_DAY * consts.DAYS_VULNS_FETCH))
        return vulns_list

    def get_device_list(self):
        try:
            self._get_assets()
        except Exception:
            logger.exception('Couldnt get export trying to do benchmark')
            return self._get_device_list_csv(), 'csv'
        try:
            vulns_list = self._get_vulns()
        except Exception:
            vulns_list = []
            logger.exception('General error while getting vulnerabilities')
        for vuln_raw in vulns_list:
            try:
                # Trying to find the correct asset for all vulnerability line in the array
                asset_id_for_vuln = vuln_raw.get('asset', {}).get('uuid', '')
                if asset_id_for_vuln is None or asset_id_for_vuln == '':
                    logger.warning(f'No id for vuln {vuln_raw}')
                    continue
                self._assets_list_dict[asset_id_for_vuln]['vulns_info'].append(vuln_raw)
            except Exception:
                logger.exception(f'Problem with vuln raw {vuln_raw}')
        self._epoch_last_run_time = int(time.time())
        return self._assets_list_dict.items(), 'export'

    def _get_device_list_csv(self):
        file_id = self._get('workbenches/export', url_params={'format': 'csv',
                                                              'report': 'vulnerabilities',
                                                              'chapter': 'vuln_by_asset',
                                                              'date_range': consts.DAYS_FOR_VULNS_IN_CSV})['file']
        status = self._get(f'workbenches/export/{file_id}/status')['status']
        sleep_times = 0
        while status != 'ready' and sleep_times < consts.NUMBER_OF_SLEEPS:
            time.sleep(consts.TIME_TO_SLEEP)
            status = self._get(f'workbenches/export/{file_id}/status')['status']
            sleep_times += 1
        return make_dict_from_csv(self._get(f'workbenches/export/{file_id}/download',
                                            use_json_in_response=False).decode('utf-8'))

    def get_agents(self):
        agents_raw = []
        try:
            scanners = self._get('scanners')['scanners']
            logger.info(f'Got {len(scanners)} scanners')
            scanners_ids = [scanner.get('id') for scanner in scanners]
            for scanner_id in scanners_ids:
                try:
                    response = self._get(f'scanners/{scanner_id}/agents', url_params={'offset': 0,
                                                                                      'limit': consts.AGENTS_PER_PAGE})
                    total = response['pagination']['total']
                    logger.info(f'Got {total} number of agents in {scanner_id}')
                    agents_raw.extend(response['agents'])
                    offset = consts.AGENTS_PER_PAGE
                    while offset < min(total, consts.MAX_AGENTS):
                        try:
                            agents_raw.extend(self._get(f'scanners/{scanner_id}/agents',
                                                        url_params={'offset': offset,
                                                                    'limit': consts.AGENTS_PER_PAGE})['agents'])
                        except BaseException:
                            logger.exception(f'Problem with offset {offset}')
                        offset += consts.MAX_AGENTS
                except Exception:
                    logger.exception(f'Problem getting agents from scanner id {scanner_id}')
            return agents_raw
        except Exception:
            logger.exception(f'Problem getting agents return []')
            return agents_raw
