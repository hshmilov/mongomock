import logging

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from tenable_security_center_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


class TenableSecurityScannerConnection(RESTConnection):
    # This code heavily relies on pyTenable https://github.com/tenable/pyTenable/blob/
    # 24e0fbd6191907b46c4e2e1b6cee176e93ad6d4d/tenable/securitycenter/securitycenter.py
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

    # pylint: disable=W0221
    def _do_request(self, *args, **kwargs):
        resp = super()._do_request(*args, **kwargs)

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
        if not ips or not asset_name:
            raise RESTException('Missing IPS or Asset ID')
        asset_list = self._get('asset')
        if not asset_list or not isinstance(asset_list, list):
            raise RESTException('Bad list of assets')
        asset_id = None
        for asset_raw in asset_list:
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
        for ip in ips:
            if ip not in ips_raw:
                ips_raw.add(ip)
        self._patch('asset',
                    body_params={'definedIPs': ','.join(ips_raw), 'id': asset_id})
        return True

    def create_asset_with_ips(self, tenable_sc_dict):
        asset_name = tenable_sc_dict.get('asset_name')
        ips = tenable_sc_dict.get('ips')
        if not ips or not asset_name:
            raise RESTException('Missing IPS or Asset ID')
        self._post('asset', body_params={'definedIPs': ','.join(ips), 'name': asset_name, 'type': 'static'})
        return True

    def get_device_list(self):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id') for repository in repositories if repository.get('id')]
        for repository_id in repositories_ids:
            try:
                yield from self.get_device_list_from_analysis(repository_id, 'vuln', 'cumulative',
                                                              'sumip', 'vuln')
            except Exception:
                logger.exception(f'Problem with repository {repository_id}')

    def get_device_list_from_analysis(self, repository_id, analysis_type, source_type, query_tool, query_type):
        start_offest = 0
        end_offset = consts.DEVICE_PER_PAGE
        # This API is half documented. Ofri got this API after playing with the instance
        response = self._post('analysis', body_params={'type': analysis_type,
                                                       'sourceType': source_type,
                                                       'query': {'tool': query_tool,
                                                                 'type': query_type,
                                                                 'startOffset': start_offest,
                                                                 'endOffset': end_offset,
                                                                 'filters': [{
                                                                     'filterName': 'repository', 'id': 'repository',
                                                                     'isPredefined': True, 'operator': '=',
                                                                     'type': query_type,
                                                                     'value': [{'id': repository_id}]
                                                                 }]}})
        start_offest += consts.DEVICE_PER_PAGE
        end_offset += consts.DEVICE_PER_PAGE
        yield from response['results']
        total_records = response['totalRecords']
        records_returned = response['returnedRecords']
        logger.info(f'Got {records_returned} out of {total_records} at the first page')
        while int(start_offest) < int(total_records) \
                and int(start_offest) < int(consts.MAX_RECORDS):
            try:
                response = self._post('analysis', body_params={'type': analysis_type,
                                                               'sourceType': source_type,
                                                               'query': {'tool': query_tool,
                                                                         'type': query_type,
                                                                         'startOffset': start_offest,
                                                                         'endOffset': end_offset}})
                yield from response['results']
                records_returned = response['returnedRecords']
                logger.info(f'Got {records_returned} out of {total_records} at offset {start_offest}')
            except Exception:
                logger.exception(f'Problems at offset {start_offest}')
            start_offest += consts.DEVICE_PER_PAGE
            end_offset += consts.DEVICE_PER_PAGE
