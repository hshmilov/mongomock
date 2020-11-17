import logging

from collections import defaultdict
from datetime import datetime
from typing import List

from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.tenable_sc import consts
from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class TenableSecurityScannerConnection(RESTConnection):
    # This code heavily relies on pyTenable https://github.com/tenable/pyTenable/blob/
    # 24e0fbd6191907b46c4e2e1b6cee176e93ad6d4d/tenable/securitycenter/securitycenter.py

    def __init__(self, *args, token=None, **kwargs):
        super().__init__(*args, url_base_prefix='/rest/',
                         headers={'Content-Type': 'application/json',
                                  'Accept': 'application/json'}, **kwargs)
        self._token = token

    def _connect(self):
        if (not self._username or not self._password) and not self._token:
            raise RESTException('Credentials must include username and password or Token')
        if not self._token:
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
            self._session_headers['X-SecurityCenter'] = self._token
        self._get('repository')

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
            if not self._token:
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

    def _get_device_list(self, repository_id):
        try:
            yield from self.do_analysis(repository_id=repository_id,
                                        analysis_type='vuln',
                                        source_type='cumulative',
                                        query_tool='sumip',
                                        query_type='vuln')
        except Exception:
            logger.exception(f'Problem with repository {repository_id}')

    # pylint: disable=arguments-differ, too-many-nested-blocks, too-many-branches, too-many-locals
    def get_device_list(self, drop_only_ip_devices, top_n_software=0,
                        per_device_software=False, fetch_vulnerabilities=False,
                        info_vulns_plugin_ids: List[str] = None, fetch_scap=False,
                        fetch_asset_groups=False, async_chunks=50):
        repositories = self._get('repository')
        repositories_ids = [repository.get('id') for repository in repositories if repository.get('id')]
        for repository_id in repositories_ids:
            try:
                device_list = self._get_device_list(repository_id=repository_id)
                if drop_only_ip_devices:
                    logger.info(f'Dropping devices with only IP address')

                if fetch_vulnerabilities:
                    logger.info(f'Fetching vulnerabilities')
                    vuln_mapping = self._get_vuln_mapping(repository_id=repository_id,
                                                          info_vulns_plugin_ids=info_vulns_plugin_ids)

                if per_device_software:
                    logger.info(f'Fetching all software for each device')

                if top_n_software:
                    logger.info(f'Fetching top {top_n_software} installed software')
                    software_mapping = self._get_software_device_mapping(top_n=top_n_software,
                                                                         repository_id=repository_id)

                if fetch_scap:
                    logger.info(f'Fetching SCAP scans')
                    scap_mapping = self._get_scap_mapping(repository_id=repository_id)

                if fetch_asset_groups:
                    logger.info(f'Start fetching asset groups')
                    asset_groups_mapping = self._get_asset_groups_mapping(repository_id=repository_id,
                                                                          device_list=device_list,
                                                                          async_chunks=async_chunks)

                for device in device_list:
                    device['software'] = []
                    if drop_only_ip_devices:
                        dns_name = device.get('dnsName')
                        mac_address = device.get('macAddress')
                        netbios_name = device.get('netbiosName')
                        if not any([dns_name, mac_address, netbios_name]):
                            continue
                    if top_n_software:
                        for software, devices in software_mapping.items():
                            if self._software_id(device) in devices:
                                device['software'].append(software)
                    if per_device_software:
                        device_ip = device.get('ip')
                        device_dns = device.get('dnsName')
                        if not any([device_dns, device_ip]):
                            continue
                        for software in self._get_software_per_device(device_ip=device_ip,
                                                                      device_dns=device_dns,
                                                                      repository_id=repository_id):
                            if software.get('name'):
                                device['software'].append(software.get('name'))
                    if fetch_vulnerabilities:
                        device['vulnerabilities'] = vuln_mapping.get(self._vuln_id(device)) or []
                    if fetch_scap:
                        device['scap'] = scap_mapping.get(self._vuln_id(device)) or []
                    if fetch_asset_groups and device.get('uuid'):
                        device['asset_groups'] = asset_groups_mapping.get(device.get('uuid'))
                    yield device

            except Exception:
                logger.exception(f'Failed to get device list for repository {repository_id}')

    # pylint: enable=arguments-differ, too-many-nested-blocks, too-many-branches

    def _get_vuln_list(self, repository_id, vulns_plugin_ids=None):
        try:
            plugin_ids = None
            if isinstance(vulns_plugin_ids, list):
                plugin_ids = ','.join(vulns_plugin_ids)

            if plugin_ids:
                filter_ = {'filterName': 'pluginID',
                           'operator': '=',
                           'type': 'vuln',
                           'value': plugin_ids}

                yield from self.do_analysis(repository_id=repository_id,
                                            analysis_type='vuln',
                                            source_type='cumulative',
                                            query_tool='vulndetails',
                                            query_type='vuln',
                                            extra_filter=filter_)
        except Exception:
            logger.exception(f'Problem with repository {repository_id} for specific plugin ids')

        filter_ = {'filterName': 'severity',
                   'id': 'severity',
                   'isPredefined': True,
                   'operator': '=',
                   'type': 'vuln',
                   'value': ','.join(consts.VULN_SEVERITY_ID_ALL_BUT_INFO)}

        mitigated = defaultdict(list)
        try:
            # Only fetching lastMitigated field and enriching the vuln data - key is unique (pluginid, ip, port)
            # https://docs.tenable.com/tenablesc/Content/CumulativeMitigatedVulnerabilities.htm#Mitigate
            for vuln in self.do_analysis(repository_id=repository_id,
                                         analysis_type='vuln',
                                         source_type='patched',
                                         query_tool='vulndetails',
                                         query_type='vuln',
                                         extra_filter=filter_):
                if isinstance(vuln, dict) and vuln.get('lastMitigated') and vuln.get('pluginID') and vuln.get(
                        'ip') and vuln.get('port'):
                    key = (vuln.get('pluginID'), vuln.get('ip'), vuln.get('port'))
                    last_mitigated = parse_date(vuln.get('lastMitigated'))
                    if isinstance(last_mitigated, datetime):
                        mitigated[key].append(last_mitigated)

        except Exception as e:
            logger.exception(f'Problem with fetching from patched repository {repository_id}, {str(e)}')

        try:
            for vuln in self.do_analysis(repository_id=repository_id,
                                         analysis_type='vuln',
                                         source_type='cumulative',
                                         query_tool='vulndetails',
                                         query_type='vuln',
                                         extra_filter=filter_):
                if isinstance(vuln, dict):
                    try:
                        key = (vuln.get('pluginID'), vuln.get('ip'), vuln.get('port'))
                        vuln['lastMitigated'] = max(mitigated.get(key)) if mitigated.get(key) else None
                    except Exception:
                        logger.warning(f'Failed parsing last mitigated for key: {key} in dict: {mitigated}')
                yield vuln

        except Exception:
            logger.exception(f'Problem with repository {repository_id}')

    @staticmethod
    def _is_info_vuln(vuln_dict):
        severity = vuln_dict.get('severity')
        if not isinstance(severity, dict):
            return False

        severity_id = severity.get('id')
        if not isinstance(severity_id, str):
            return False

        return severity_id == consts.VULN_SEVERITY_ID_INFO

    def _get_asset_groups_mapping(self, repository_id: int, device_list: list, async_chunks: int):
        try:
            asset_groups_mapping = {}

            assets_groups_raw_requests = []
            device_info_list = []
            for device in device_list:
                if not (isinstance(device, dict) and device.get('uuid') and device.get('ip') and device.get('dnsName')):
                    continue
                device_info_list.append((device.get('uuid'), device.get('ip'), device.get('dnsName')))
                assets_groups_raw_requests.append({
                    'name': f'repository/{repository_id}/assetIntersections',
                    'url_params': {
                        'ip': device.get('ip'),
                        'dnsName': device.get('dnsName')}
                })

            for (uuid, _, _), response in zip(device_info_list, self._async_get(assets_groups_raw_requests,
                                                                                retry_on_error=True,
                                                                                chunks=async_chunks,
                                                                                copy_cookies=True)):
                if not self._is_async_response_good(response):
                    logger.error(f'Async response returned bad, its {response}')
                    continue
                if not (isinstance(response, dict) and
                        isinstance(response.get('response'), dict) and
                        isinstance(response.get('response').get('assets'), list)):
                    logger.warning(f'Invalid response returned: {response}')
                    continue

                asset_groups_mapping[uuid] = response.get('response').get('assets')

            return asset_groups_mapping
        except Exception:
            logger.exception(f'Failed to fetch asset groups')
            return asset_groups_mapping

    def _get_vuln_mapping(self, repository_id, info_vulns_plugin_ids):
        result = defaultdict(list)
        vuln_list = self._get_vuln_list(repository_id, vulns_plugin_ids=info_vulns_plugin_ids) or []
        for vuln in vuln_list:
            vuln_id = self._vuln_id(vuln)
            if not vuln_id:
                continue

            result[vuln_id].append(vuln)
        return dict(result)

    def _get_scap_list(self, repository_id):
        filter_ = {
            'filterName': 'pluginType',
            'id': 'pluginType',
            'isPredefined': True,
            'operator': '=',
            'type': 'vuln',
            'value': 'compliance',
        }

        try:
            yield from self.do_analysis(repository_id=repository_id,
                                        analysis_type='vuln',
                                        source_type='individual',
                                        query_tool='sumid',
                                        query_type='vuln',
                                        extra_filter=filter_)
        except Exception:
            logger.exception(f'Problem with repository {repository_id}')

    def _get_scap_mapping(self, repository_id):
        scap_mapping = defaultdict(list)
        scap_list = self._get_scap_list(repository_id) or []
        for scap in scap_list:
            scap_id = self._vuln_id(scap)
            if not scap_id:
                continue

            scap_mapping[scap_id].append(scap)
        return dict(scap_mapping)

    @staticmethod
    def _vuln_id(device):
        ip = device.get('ip')
        mac = device.get('macAddress')
        netbios = device.get('netbiosName')
        if not any([ip, mac, netbios]):
            return None
        return '_'.join([ip, mac, netbios])

    def _get_software_list(self, top_n, repository_id):
        try:
            yield from self.do_analysis(repository_id,
                                        'vuln',
                                        'cumulative',
                                        'listsoftware',
                                        'vuln',
                                        count=top_n)
        except Exception:
            logger.exception(f'Problem with repository {repository_id}')

    def _get_devices_by_software(self, software_name, repository_id):
        filter_ = {
            'filterName': 'pluginText',
            'id': 'pluginText',
            'isPredefined': True,
            'operator': '=',
            'type': 'vuln',
            'value': software_name,
        }
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

    def _get_software_device_mapping(self, top_n, repository_id):
        result = {}
        software_list = self._get_software_list(top_n=top_n, repository_id=repository_id)
        software_list = set(filter(None, [device.get('name') for device in software_list]))
        for software in software_list:
            try:
                devices = self._get_devices_by_software(software_name=software, repository_id=repository_id)
                result[software] = list(filter(None, [(self._software_id(device)) for device in devices]))
            except Exception:
                logger.exception(f'Failed to fetch device list for software {software}')
        return result

    def _get_software_per_device(self, device_ip=None, device_dns=None, repository_id=None):
        filter_ = [
            {
                'filterName': 'ip',
                'id': 'ip',
                'isPredefined': True,
                'operator': '=',
                'type': 'vuln',
                'value': device_ip
            },
            {
                'filterName': 'dnsName',
                'id': 'dnsName',
                'isPredefined': True,
                'operator': '=',
                'type': 'vuln',
                'value': device_dns
            }
        ]
        try:
            yield from self.do_analysis(repository_id=repository_id,
                                        analysis_type='vuln',
                                        source_type='cumulative',
                                        query_tool='listsoftware',
                                        query_type='vuln',
                                        extra_filter=filter_)
        except Exception:
            logger.exception(f'Problem with repository {repository_id}')

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

                if isinstance(extra_filter, list):
                    for filter_ in extra_filter:
                        if filter_.get('value'):
                            body_params['query']['filters'].append(filter_)

                if isinstance(extra_filter, dict):
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
