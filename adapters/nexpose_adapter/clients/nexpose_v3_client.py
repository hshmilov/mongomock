import datetime
import logging
import math

import aiohttp
import requests
import urllib3

from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import (ClientConnectionException,
                                        GetDevicesError)
from axonius.async.utils import async_request
from axonius.utils.json import from_json
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import figure_out_cloud
from axonius.fields import Field, ListField

from nexpose_adapter.clients.nexpose_base_client import NexposeClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(f'axonius.{__name__}')
MAX_ASYNC_REQUESTS_IN_PARALLEL = 100


class ScanData(SmartJsonClass):
    engine_name = Field(str, 'Engine Name')
    duration = Field(str, 'Duration')
    status = Field(str, 'Scan Status')
    site_name = Field(str, 'Site Name')
    start_time = Field(datetime.datetime, 'Start Time')
    scan_type = Field(str, 'Scan Type')
    scan_name = Field(str, 'Scan Name')
    end_time = Field(datetime.datetime, 'End Time')


class PciStatus(SmartJsonClass):
    adjusted_cvss_score = Field(int, 'Adjusted CVSS Score')
    adjusted_severity_score = Field(int, 'Adjusted Severity Score')
    fail = Field(bool, 'Fail')
    status = Field(str, 'Status')


class NexposeVuln(SmartJsonClass):
    added = Field(datetime.datetime, 'Added')
    categories = ListField(str, 'Categories')
    cves = ListField(str, 'CVEs')
    denial_of_service = Field(bool, 'Denial Of Service')
    description = Field(str, 'Description')
    exploits = Field(int, 'Exploits')
    malware_kits = Field(int, 'Malware Kits')
    modified = Field(datetime.datetime, 'Modified')
    published = Field(datetime.datetime, 'Published')
    risk_score = Field(float, 'Risk Score')
    severity = Field(str, 'Severity')
    severity_score = Field(int, 'Severity Score')
    title = Field(str, 'Title')
    pci = Field(PciStatus, 'PCI Data')


class NexposeV3Client(NexposeClient):

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def _get_async_data(self, devices, data_type):
        # Get all tags for all devices asynchronously
        # Build the requests
        aio_requests = []
        aio_ids = []
        for i, item in enumerate(devices):
            item_id = item.get('id')
            if not item_id:
                logger.warning('Got device with no id, not yielding')
                continue

            aio_req = dict()
            aio_req['method'] = 'GET'
            aio_req['url'] = f'https://{self.host}:{self.port}/api/3/assets/{item_id}/{data_type}'
            if data_type == 'vulnerabilities':
                aio_req['url'] += '?size=500'
            aio_req['auth'] = (self.username, self.password)
            headers = None
            if self._token:
                headers = {'Token': self._token}
            if headers:
                aio_req['headers'] = headers
            aio_req['timeout'] = (5, 30)

            if self.verify_ssl is False:
                aio_req['ssl'] = False
            aio_requests.append(aio_req)
            aio_ids.append(i)

        for chunk_id in range(int(math.ceil(len(aio_requests) / MAX_ASYNC_REQUESTS_IN_PARALLEL))):
            logger.debug(
                f'Async requests: sending {chunk_id * MAX_ASYNC_REQUESTS_IN_PARALLEL} out of {len(aio_requests)}')

            all_answers = async_request(
                aio_requests[MAX_ASYNC_REQUESTS_IN_PARALLEL * chunk_id:
                             MAX_ASYNC_REQUESTS_IN_PARALLEL * (chunk_id + 1)])

            # We got the requests,
            # time to check if they are valid and transform them to what the user wanted.

            for i, raw_answer in enumerate(all_answers):
                request_id_absolute = MAX_ASYNC_REQUESTS_IN_PARALLEL * chunk_id + i
                current_device = devices[aio_ids[request_id_absolute]]
                try:
                    # The answer could be an exception
                    if isinstance(raw_answer, Exception):
                        logger.debug(f'Exception getting tags for request {request_id_absolute}, yielding'
                                     f' device with no tags. Data type {data_type}. Exception {raw_answer}')

                    # Or, it can be the actual response
                    elif isinstance(raw_answer, tuple) and isinstance(raw_answer[0], str) \
                            and isinstance(raw_answer[1], aiohttp.ClientResponse):
                        text_answer = raw_answer[0]
                        response_object = raw_answer[1]

                        try:
                            response_object.raise_for_status()
                            current_device[f'{data_type}_details'] = from_json(text_answer)['resources']
                        except aiohttp.ClientResponseError as e:
                            logger.debug(f'async error code {e.status} on '
                                         f'request id {request_id_absolute}. '
                                         f'original response is {raw_answer}. Yielding with no tags')
                        except Exception:
                            logger.debug(f'Exception while parsing async response for {text_answer}'
                                         f'. Yielding with no tags')
                    else:
                        msg = f'Got an async response which is not exception or ClientResponse. ' \
                              f'This should never happen! response is {raw_answer}'
                        logger.critical(msg)
                except Exception:
                    msg = f'Error while parsing request {request_id_absolute} - {raw_answer}, continuing'
                    logger.exception(msg)

    def _get_scans(self):
        scans_dict = dict()
        try:
            num_of_scans_pages = 1
            current_page_num = -1

            # for current_page_num in range(1, num_of_asset_pages):
            while current_page_num < num_of_scans_pages:
                try:
                    current_page_num += 1
                    current_page_response_as_json = self._send_get_request(
                        'scans', {'page': current_page_num, 'size': self.num_of_simultaneous_devices})
                    scans = current_page_response_as_json.get('resources', [])
                    num_of_scans_pages = current_page_response_as_json.get('page', {}).get('totalPages')
                    for scan_raw in scans:
                        if scan_raw.get('id'):
                            scans_dict[scan_raw['id']] = scan_raw

                except Exception:
                    logger.exception(f'Got exception while fetching page {current_page_num+1} '
                                     f'(api page {current_page_num}).')
                    continue
                if current_page_num % (max(1, round(num_of_scans_pages / 100))) == 0:
                    logger.info(
                        f'Got {current_page_num} out of {num_of_scans_pages} pages. '
                        f'({(current_page_num / max(num_of_scans_pages, 1)) * 100}% of scans pages).')

        except Exception as err:
            logger.exception('Error getting the nexpose scans.')
        return scans_dict

    # pylint: disable=arguments-differ
    def get_all_devices(self, fetch_tags=False, fetch_vulnerabilities=False):
        logger.info(f'Stating to fetch devices on V3 for nexpose')
        scans_dict = self._get_scans()
        self.vuln_ids_dict = {}
        try:
            num_of_asset_pages = 1
            current_page_num = -1

            # for current_page_num in range(1, num_of_asset_pages):
            while current_page_num < num_of_asset_pages:
                try:
                    current_page_num += 1
                    current_page_response_as_json = self._send_get_request(
                        'assets', {'page': current_page_num, 'size': self.num_of_simultaneous_devices})
                    devices = current_page_response_as_json.get('resources', [])
                    num_of_asset_pages = current_page_response_as_json.get('page', {}).get('totalPages')
                    for item in devices:
                        item.update({'API': '3'})
                        item['vulnerability_details_full'] = []
                        item['scans_raw'] = []
                        try:
                            for scan_item in item['history']:
                                if scan_item.get('scanId'):
                                    scan_id = scan_item.get('scanId')
                                    if scans_dict.get(scan_id):
                                        item['scans_raw'].append(scans_dict.get(scan_id))
                        except Exception:
                            logger.exception(f'Problem parsing history')
                    if fetch_vulnerabilities:
                        self._get_async_data(devices, 'vulnerabilities')
                        for item in devices:
                            for vuln in item.get('vulnerabilities_details') or []:
                                try:
                                    vuln_id = vuln.get('id')
                                    vuln_details = self.get_vuln_details(vuln_id=vuln_id) or {}
                                    item['vulnerability_details_full'].append(vuln_details)
                                except Exception:
                                    logger.exception(f'Problem getting details for vulnerability {vuln_id}')

                    if fetch_tags:
                        self._get_async_data(devices, 'services')
                        self._get_async_data(devices, 'tags')
                        self._get_async_data(devices, 'software')
                    yield from devices

                except Exception:
                    logger.exception(f'Got exception while fetching page {current_page_num+1} '
                                     f'(api page {current_page_num}).')
                    continue

                # num_of_asset_pages might be something that dividing by 100 could lead us to no prints at all like
                # 188 pages.
                if current_page_num % (max(1, round(num_of_asset_pages / 100))) == 0:
                    logger.info(
                        f'Got {current_page_num} out of {num_of_asset_pages} pages. '
                        f'({(current_page_num / max(num_of_asset_pages, 1)) * 100}% of device pages).')

        except Exception as err:
            logger.exception('Error getting the nexpose devices.')
            raise GetDevicesError('Error getting the nexpose devices.')

    def get_vuln_details(self, vuln_id):
        if vuln_id in self.vuln_ids_dict:
            return self.vuln_ids_dict[vuln_id]
        try:
            headers = None
            if self._token:
                headers = {'Token': self._token}
            vuln_details = requests.get(f'https://{self.host}:{self.port}/api/3/vulnerabilities/{vuln_id}',
                                        auth=(self.username, self.password),
                                        verify=self.verify_ssl,
                                        timeout=(30, 300),
                                        headers=headers)
            self.vuln_ids_dict[vuln_id] = vuln_details.json()
            return self.vuln_ids_dict[vuln_id]
        except Exception:
            logger.exception(f'Problem getting vulnerability details for {vuln_id}')

    def get_vulnerabilities_for_device(self, device):
        try:
            device_id = device.get('id')
            device_vulns = []
            headers = None
            if self._token:
                headers = {'Token': self._token}
            vulnerabilities = requests.get(f'https://{self.host}:{self.port}/api/3/assets/{device_id}/vulnerabilities',
                                           params={'size': 500},
                                           auth=(self.username, self.password),
                                           verify=self.verify_ssl,
                                           timeout=(30, 300),
                                           headers=headers)
            vulnerabilities = vulnerabilities.json()
            for vuln in vulnerabilities.get('resources') or []:
                try:
                    vuln_id = vuln.get('id')
                    vuln_details = self.get_vuln_details(vuln_id=vuln_id) or {}
                    device_vulns.append(vuln_details)
                except Exception:
                    logger.exception(f'Problem getting details for vulnerability {vuln_id}')
            yield from device_vulns

        except Exception:
            logger.exception(f'Problem getting vulnerability data for device')

    def _send_get_request(self, resource, params=None):
        """
        Sends a get request to the client (authenticated, and ssl_verified configured).
        :param resource: The restful resource to get.
        :param params: The params of the get request.
        :return: The response of the get request.
        """
        def _parse_dedicated_url(resource):
            return f'https://{self.host}:{self.port}/api/3/{resource}'

        try:
            headers = None
            if self._token:
                headers = {'Token': self._token}
            response = requests.get(_parse_dedicated_url(resource), params=params,
                                    auth=(self.username, self.password), verify=self.verify_ssl,
                                    timeout=(10, 300), headers=headers)
            response.raise_for_status()
            response = response.json()
        except requests.HTTPError as e:
            raise ClientConnectionException(str(e))

        return response

    def _does_api_exist(self):
        """ Sends a get request to the api root to see if the api version exists.

        :param client_config: The configure of the client to test.
        :return: bool that signifies if this api version exists on the client.
        """
        logger.info(f'Checking API for nexpose V3')
        self._send_get_request('')

        # The get request would have raised exception if status_code wasn't 200 on response.raise_for_status().
        return True

    # pylint: disable=arguments-differ, too-many-locals, too-many-branches, too-many-statements
    @staticmethod
    def parse_raw_device(device_raw, device_class, drop_only_ip_devices=False, fetch_vulnerabilities=False):
        last_seen = device_raw.get('history', [])[-1].get('date') if device_raw.get('history', []) else None

        last_seen = super(NexposeV3Client, NexposeV3Client).parse_raw_device_last_seen(last_seen)

        device = device_class()
        device.figure_os(' '.join([device_raw.get('osFingerprint', {}).get('description', ''),
                                   device_raw.get('osFingerprint', {}).get('architecture', '')]))
        device.last_seen = last_seen
        device.id = str(device_raw['id']) + (device_raw.get('hostName') or '')
        device.nexpose_id = str(device_raw['id'])
        got_mac = False
        for address in device_raw.get('addresses', []):
            if address.get('mac'):
                got_mac = True
            device.add_nic(address.get('mac'), [address.get('ip')] if ('ip' in address and
                                                                       isinstance(address.get('ip'), str) and
                                                                       address.get('ip') != '0.0.0.0') else [])
        if not device_raw.get('hostName') and not got_mac and drop_only_ip_devices:
            return None
        device.hostname = device_raw.get('hostName')
        device.nexpose_type = device_raw.get('type')
        scans_raw = device_raw.get('scans_raw')
        for scan_raw in scans_raw:
            try:
                device.scans_data.append(ScanData(engine_name=scan_raw.get('engineName'),
                                                  duration=scan_raw.get('duration'),
                                                  status=scan_raw.get('status'),
                                                  site_name=scan_raw.get('siteName'),
                                                  scan_type=scan_raw.get('scanType'),
                                                  scan_name=scan_raw.get('scanName'),
                                                  start_time=parse_date(scan_raw.get('startTime')),
                                                  end_time=parse_date(scan_raw.get('endTime'))
                                                  ))
            except Exception:
                logger.exception(f'Problem with scan raw {scan_raw}')
        device.assessed_for_policies = device_raw.get('assessedForPolicies') \
            if isinstance(device_raw.get('assessedForPolicies'), bool) else None
        device.assessed_for_vulnerabilities = device_raw.get('assessedForVulnerabilities') \
            if isinstance(device_raw.get('assessedForVulnerabilities'), bool) else None
        if isinstance(device_raw.get('users'), list):
            for user_raw in device_raw.get('users'):
                if isinstance(user_raw, dict) and user_raw.get('name'):
                    device.last_used_users.append(user_raw.get('name'))

        risk_score = device_raw.get('riskScore')
        if risk_score is not None:
            try:
                device.risk_score = float(risk_score)
            except Exception:
                logger.exception('Cant get risk score')
        try:
            vulnerabilities_raw = device_raw.get('vulnerabilities', {})
            device.vulnerabilities_critical = vulnerabilities_raw.get('critical')
            device.vulnerabilities_exploits = vulnerabilities_raw.get('exploits')
            device.vulnerabilities_malwareKits = vulnerabilities_raw.get('malwareKits')
            device.vulnerabilities_moderate = vulnerabilities_raw.get('moderate')
            device.vulnerabilities_severe = vulnerabilities_raw.get('severe')
            device.vulnerabilities_total = vulnerabilities_raw.get('total')
        except Exception:
            logger.exception(f'Problem getting vulns for {device_raw}')

        try:
            for id_element in device_raw.get('ids', []):
                cloud_type = figure_out_cloud(id_element.get('source'))
                if cloud_type is not None:
                    device.cloud_provider = cloud_type
                    device.cloud_id = id_element.get('id')
                    break

        except Exception:
            logger.exception(f'Error getting ids array from Rapid7 Nexpose: {device_raw.get("ids")}')

        if fetch_vulnerabilities:
            try:
                device.software_cves = []
                for vuln in device_raw.get('vulnerability_details_full') or []:
                    for cve in vuln.get('cves') or []:
                        device.add_vulnerable_software(cve_id=cve)
                    try:
                        added = parse_date(vuln.get('added'))
                        cves = vuln.get('cves') if isinstance(vuln.get('cves'), list) else None
                        categories = vuln.get('categories') if isinstance(vuln.get('categories'), list) else None

                        denial_of_service = vuln.get('denialOfService') \
                            if isinstance(vuln.get('denialOfService'), bool) else None
                        description = vuln.get('description').get('text') \
                            if isinstance(vuln.get('description'), dict) else None
                        exploits = vuln.get('exploits') \
                            if isinstance(vuln.get('exploits'), int) else None
                        malware_kits = vuln.get('malwareKits') \
                            if isinstance(vuln.get('malwareKits'), int) else None
                        modified = parse_date(vuln.get('modified'))
                        published = parse_date(vuln.get('published'))
                        risk_score = None
                        try:
                            risk_score = float(vuln.get('riskScore'))
                        except Exception:
                            pass
                        severity = vuln.get('severity')
                        severity_score = vuln.get('severityScore') \
                            if isinstance(vuln.get('severityScore'), int) else None
                        title = vuln.get('title')
                        pci_raw = vuln.get('pci') if isinstance(vuln.get('pci'), dict) else {}
                        pci_fail = pci_raw.get('fail') if isinstance(pci_raw.get('fail'), bool) else None
                        pci_status = pci_raw.get('status')
                        adjusted_cvss_score = pci_raw.get('adjustedCVSSScore') \
                            if isinstance(pci_raw.get('adjustedCVSSScore'), int) else None
                        adjusted_severity_score = pci_raw.get('adjustedSeverityScore') \
                            if isinstance(pci_raw.get('adjustedSeverityScore'), int) else None
                        pci = PciStatus(fail=pci_fail,
                                        status=pci_status,
                                        adjusted_cvss_score=adjusted_cvss_score,
                                        adjusted_severity_score=adjusted_severity_score
                                        )
                        nexpose_vuln = NexposeVuln(added=added,
                                                   categories=categories,
                                                   cves=cves,
                                                   denial_of_service=denial_of_service,
                                                   description=description,
                                                   exploits=exploits,
                                                   malware_kits=malware_kits,
                                                   modified=modified,
                                                   published=published,
                                                   risk_score=risk_score,
                                                   severity=severity,
                                                   severity_score=severity_score,
                                                   title=title,
                                                   pci=pci
                                                   )
                        device.nexpose_vulns.append(nexpose_vuln)
                    except Exception:
                        logger.exception(f'Problem add full vuln')
            except Exception:
                logger.exception(f'Problem adding CVES to device')

        try:
            services_raw = device_raw.get('services_details') or []
            if services_raw and isinstance(services_raw, list):
                for services_data in services_raw:
                    try:
                        service_port = services_data.get('port')
                        service_protocol = services_data.get('protocol')
                        if not service_protocol or service_protocol.upper() not in ['TCP', 'UDP']:
                            service_protocol = None
                        if not service_port:
                            logger.warning(f'Bad service at device {device_raw}')
                            continue
                        device.add_open_port(port_id=service_port, protocol=service_protocol)
                    except Exception:
                        logger.exception(f'Problem adding services_data {services_data}')
        except Exception:
            logger.exception(f'Problem parsing services')

        try:
            software = device_raw.get('software_details') or []
            if software and isinstance(software, list):
                for software_data in software:
                    try:
                        sw_name = software_data.get('product')
                        sw_version = software_data.get('version')
                        sw_vendor = software_data.get('vendor')
                        if not sw_name:
                            logger.warning(f'Bad software at device {device_raw}')
                            continue
                        device.add_installed_software(name=sw_name,
                                                      vendor=sw_vendor,
                                                      version=sw_version)
                    except Exception:
                        logger.exception(f'Problem adding tag {software_data}')
        except Exception:
            logger.exception(f'Problem parsing sw')

        try:
            tags = device_raw.get('tags_details') or []
            if tags and isinstance(tags, list):
                for tag in tags:
                    try:
                        tag_type = tag.get('type')
                        tag_name = tag.get('name')
                        if not tag_type:
                            logger.warning(f'Bad tag type at device {device_raw}')
                            continue
                        if tag_type == 'location':
                            device.location_tags.append(tag_name)
                        elif tag_type == 'owner':
                            device.owner_tags.append(tag_name)
                        elif tag_type == 'criticality':
                            device.criticality_tags.append(tag_name)
                        elif tag_type == 'custom':
                            device.custom_tags.append(tag_name)
                        else:
                            logger.warning(f'Bad tags with weird type {tag_type} '
                                           f'__ {str(tag_name)} in device {device_raw}')
                    except Exception:
                        logger.exception(f'Problem adding tag {tag}')
        except Exception:
            logger.exception(f'Problem parsing tags')

        device.set_raw(device_raw)
        return device
    # pylint: enable=arguments-differ, too-many-locals, too-many-branches, too-many-statements
