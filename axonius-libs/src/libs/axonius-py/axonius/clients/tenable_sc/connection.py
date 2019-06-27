import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.tenable_sc import consts

logger = logging.getLogger(f'axonius.{__name__}')


class TenableSecurityScannerConnection(RESTConnection):
    # This code heavily relies on pyTenable https://github.com/tenable/pyTenable/blob/
    # 24e0fbd6191907b46c4e2e1b6cee176e93ad6d4d/tenable/securitycenter/securitycenter.py

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url_base_prefix='/rest/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)

    def _connect(self):
        if self._username is not None and self._password is not None:
            # Based on Tenable SCCV Documentation (https://docs.tenable.com/sccv/api/index.html)
            # and https://docs.tenable.com/sccv/api/Token.html
            # We need to post to 'token' and get the token and cookie.
            connection_dict = {'username': self._username,
                               'password': self._password,
                               'releaseSession': True}  # releaseSession is default false

            response = self._post('token', body_params=connection_dict)
            if response.get('releaseSession') is True:
                raise RESTException(f'User {self._username} has reached its maximum login limit.')

            # We don't have to set the cookie since RESTConnection does that for us (uses request.Session)
            self._session_headers['X-SecurityCenter'] = str(response['token'])
        else:
            raise RESTException('No user name or password')

    def _handle_response(self, response, raise_for_status=True, use_json_in_response=True, return_response_raw=False):
        resp = super()._handle_response(response=response,
                                        raise_for_status=raise_for_status,
                                        use_json_in_response=use_json_in_response,
                                        return_response_raw=return_response_raw)

        if not use_json_in_response:
            return resp

        try:
            if str(resp['error_code']) != '0':
                raise RESTException(f'API Error {resp["error_code"]}: {resp["error_msg"]}')
        except KeyError:
            pass

        return resp['response']

    def close(self):
        # Deletes the token associated with the logged in User (https://docs.tenable.com/sccv/api/Token.html)
        try:
            self._delete('token')
        except Exception:
            logger.exception('Couldn\'t delete token')
        super().close()

    def add_ips_to_asset(self, tenable_sc_dict):
        asset_name = tenable_sc_dict.get('asset_name')
        ips = tenable_sc_dict.get('ips')
        override = tenable_sc_dict.get('override')
        if not ips or not asset_name:
            raise RESTException('Missing IPS or Asset ID')
        asset_list = self._get('asset')
        if not asset_list or not isinstance(asset_list, dict):
            raise RESTException('Bad list of assets')
        asset_id = None
        for asset_raw in (asset_list.get('usable') or []) + (asset_list.get('manageable') or []):
            if asset_raw.get('name') == asset_name:
                asset_id = asset_raw.get('id')
                break
        if not asset_id:
            raise RESTException('Couldn\'n find asset name')
        asset_id_raw = self._get(f'asset/{asset_id}')
        if not asset_id_raw or not isinstance(asset_id_raw, dict):
            raise RESTException('Couldn\'n get asset id info')
        if not (asset_id_raw.get('typeFields') or {}).get('definedIPs'):
            raise RESTException('Device with no IPs')
        ips_raw = (asset_id_raw.get('typeFields') or {}).get('definedIPs').split(',')
        if override:
            ips_raw = []
        for ip in ips:
            if ip not in ips_raw:
                ips_raw.append(ip)
        self._patch(f'asset/{asset_id}',
                    body_params={'definedIPs': ','.join(ips_raw)})
        return True

    def create_asset_with_ips(self, tenable_sc_dict):
        asset_name = tenable_sc_dict.get('asset_name')
        ips = tenable_sc_dict.get('ips')
        if not ips or not asset_name:
            raise RESTException('Missing IPS or Asset ID')
        self._post('asset', body_params={'definedIPs': ','.join(ips), 'name': asset_name, 'type': 'static'})
        return True

    def _get_device_list(self):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id') for repository in repositories if repository.get('id')]
        for repository_id in repositories_ids:
            try:
                yield from self.do_analysis(repository_id=repository_id,
                                            analysis_type='vuln',
                                            source_type='cumulative',
                                            query_tool='sumip',
                                            query_type='vuln')
            except Exception:
                logger.exception(f'Problem with repository {repository_id}')

    # pylint: disable=arguments-differ
    def get_device_list(self, top_n_software=0):
        if not top_n_software:
            yield from self._get_device_list()
            return

        logger.info(f'Fetching top {top_n_software} installed software')
        device_list = self._get_device_list()
        software_mapping = self._get_software_device_mapping(top_n_software)

        for device in device_list:
            device['software'] = []
            for software, devices in software_mapping.items():
                if self._software_id(device) in devices:
                    device['software'].append(software)
            yield device
    # pylint: enable=arguments-differ

    def _get_software_list(self, top_n):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id') for repository in repositories if repository.get('id')]
        for repository_id in repositories_ids:
            try:
                yield from self.do_analysis(repository_id,
                                            'vuln',
                                            'cumulative',
                                            'listsoftware',
                                            'vuln',
                                            count=top_n)
            except Exception:
                logger.exception(f'Problem with repository {repository_id}')

    def _get_devices_by_software(self, software_name):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id') for repository in repositories if repository.get('id')]
        filter_ = {
            'filterName': 'pluginText',
            'id': 'pluginText',
            'isPredefined': True,
            'operator': '=',
            'type': 'vuln',
            'value': software_name,
        }
        for repository_id in repositories_ids:
            try:
                yield from self.do_analysis(repository_id=repository_id,
                                            analysis_type='vuln',
                                            source_type='cumulative',
                                            query_tool='sumip',
                                            query_type='vuln',
                                            extra_filter=filter_)
            except Exception:
                logger.exception(f'Problem with repository {repository_id}')

    @staticmethod
    def _software_id(device):
        uuid = device.get('uuid')
        biosGUID = device.get('biosGUID')

        if not any([uuid, biosGUID]):
            return None
        return '_'.join([uuid, biosGUID])

    def _get_software_device_mapping(self, top_n):
        result = {}
        software_list = self._get_software_list(top_n)
        software_list = set(filter(None, [device.get('name') for device in software_list]))
        for software in software_list:
            try:
                devices = self._get_devices_by_software(software)
                result[software] = list(filter(None, [(self._software_id(device)) for device in devices]))
            except Exception:
                logger.exception(f'Failed to fetch device list for software {software}')
        return result

    def do_analysis(self,
                    repository_id,
                    analysis_type,
                    source_type,
                    query_tool,
                    query_type,
                    extra_filter=None,
                    count=int(consts.MAX_RECORDS)):

        # This API is half documented. Ofri got this API after playing with the instance

        start_offset = 0
        end_offset = 0
        total_records_got = 0
        exception_count = 0

        while True:
            try:
                start_offset = end_offset
                end_offset += min([consts.DEVICE_PER_PAGE, (count - start_offset)])

                if start_offset >= count:
                    break

                if exception_count > consts.MAX_EXCEPTION_THRESHOLD:
                    logger.info(f'Too many exception giving up on repo {repository_id}')
                    break

                body_params = {'type': analysis_type,
                               'sourceType': source_type,
                               'query': {'tool': query_tool,
                                         'type': query_type,
                                         'startOffset': start_offset,
                                         'endOffset': end_offset,
                                         'filters': [{
                                             'filterName': 'repository', 'id': 'repository',
                                             'isPredefined': True, 'operator': '=',
                                             'type': query_type,
                                             'value': [{'id': repository_id}]
                                         }]}}
                if extra_filter:
                    body_params['query']['filters'].append(extra_filter)

                response = self._post('analysis',
                                      body_params=body_params,
                                      raise_for_status=False,
                                      return_response_raw=True,
                                      use_json_in_response=False)

                if response.status_code == 403:
                    logger.warning(f'{repository_id}: Permission problem for repo giving up')
                    break

                response = self._handle_response(response)

                total_records = response['totalRecords']  # WARNING: BUG: total records number might be wrong!
                records = response['results']
                records_returned = len(records)
                total_records_got += records_returned

                yield from records

                logger.info(f'{repository_id}: Got {total_records_got} out of {total_records} at offset {start_offset}')

                # if we got less records then requested -> this is the last page and we should break
                if records_returned < (end_offset - start_offset):
                    break

                if total_records_got >= count:
                    break

                exception_count = 0
            except Exception:
                logger.exception(f'Problems at offset {start_offset} moving on exception_count = {exception_count}')
                exception_count += 1
                continue
